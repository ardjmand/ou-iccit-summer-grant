import matplotlib.pyplot as plt
import pandas as pd

from params import *


class Faculty:
    def __init__(self, faculty_url=faculty_url, departments=departments):
        self.faculty_url = faculty_url
        self.departments = departments
        self.journal_list = pd.read_csv("journal_list.csv")
        self.journal_match = pd.read_csv("journal_match.csv")
        self.faculty_df = None
        self.pub_df = None
        self.faculty_pub_df = None

    def load_faculty_info(self, file="faculty_df.csv"):
        dtype_mapping = {'EID': str, 'ORCID': str}
        self.faculty_df = pd.read_csv(file, dtype=dtype_mapping)

    def load_pub_info(self, file="pub_df.csv"):
        dtype_mapping = {'AU-ID': str}
        date_column_names = ['coverDate']
        self.pub_df = pd.read_csv(file, dtype=dtype_mapping, parse_dates=date_column_names)

    def load_faculty_pub(self, file="faculty_pub.csv"):
        dtype_mapping = {'AU-ID': str, 'EID': str, 'ORCID': str}
        date_column_names = ['coverDate']
        self.faculty_pub_df = pd.read_csv(file, dtype=dtype_mapping, parse_dates=date_column_names)

    def retrieve_author_id(self, author_firstname, author_lastname, author_affiliation="Ohio University"):
        query = (f"AUTHLAST({author_lastname}) and AUTHFIRST({author_firstname}) and "
                 f"AFFIL({author_affiliation}) and AFFILCITY(Athens) and "
                 f"(AF-ID(60011132) or AF-ID(60135978))")
        author_search = AuthorSearch(query=query)
        if author_search.get_results_size() > 0:
            author_orcid = author_search.authors[0].orcid
            author_eid = author_search.authors[0].eid.split('-')[-1]
        else:
            author_orcid = None
            author_eid = None

        return author_orcid, author_eid

    def scrape_info(self, save=True):
        faculty_df = pd.DataFrame(columns=["Full Name", "First Name", "Last Name",
                                           "Tenure", "Position", "Department", "ORCID", "EID"])

        driver = webdriver.Chrome()
        driver.get(self.faculty_url)
        # wait until loaded
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, 'Apply')))

        for d in self.departments:

            # select the department dropdown menu
            dropdown = driver.find_element(By.ID, "edit-department")
            select = Select(dropdown)
            select.select_by_visible_text(d)
            driver.find_element(By.ID, "edit-submit-business-faculty-and-staff").click()
            # wait until loaded
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, 'Apply')))
            time.sleep(2)

            faculty_list = [f.text for f in driver.find_elements(By.CLASS_NAME, "aProfile-name")]
            # handle name exceptions
            for n in range(len(faculty_list)):
                if faculty_list[n] in name_exceptions:
                    faculty_list[n] = name_exceptions[faculty_list[n]]


            first_names = [name.split()[0] for name in faculty_list]
            last_names = [name.split()[-1] for name in faculty_list]

            title_list = [f.text for f in driver.find_elements(By.CLASS_NAME, "aProfile-title")]
            # separate tenure and non-tenure faculty
            tenure_list = []
            for title in title_list:
                if "Instruction" in title or "Visiting" in title:
                    tenure_list.append("Instructional")
                elif re.search(r"executive[-\s]*in[-\s]*residence", title, re.IGNORECASE):
                    tenure_list.append("Executive in Residence")
                else:
                    tenure_list.append("Tenure")
            # get the rank
            rank_list = []
            for title in title_list:
                if "Assistant Professor" in title:
                    rank_list.append("Assistant Professor")
                elif "Associate Professor" in title:
                    rank_list.append("Associate Professor")
                elif "Professor" in title:
                    rank_list.append("Professor")
                else:
                    rank_list.append(None)  # If no rank keyword is found, add None

            orcid_list = []
            eid_list = []
            for f in range(len(first_names)):
                ids = self.retrieve_author_id(author_firstname=first_names[f], author_lastname=last_names[f])
                orcid_list.append(ids[0])
                eid_list.append(str(ids[1]))

            # Add the scraped data to the DataFrame
            data = {
                "Full Name": faculty_list,
                "First Name": first_names,
                "Last Name": last_names,
                "Tenure": tenure_list,
                "Position": rank_list,
                "Department": [d] * len(faculty_list),  # Set all values in the Department column to d
                "ORCID": orcid_list,
                "EID": eid_list
            }
            faculty_df = pd.concat([faculty_df, pd.DataFrame(data)], ignore_index=True)

            # reset the page. This is needed to sort out the selectors
            driver.get(self.faculty_url)
            # wait until loaded
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, 'Apply')))

        faculty_df = faculty_df.drop_duplicates(subset='Full Name', keep='last')
        self.faculty_df = faculty_df
        if save:
            faculty_df.to_csv("faculty_df.csv", index=False)

        return faculty_df

    def get_pubs(self, save=True):
        if self.faculty_df is None:
            raise TypeError("Faculty dataframe type is incorrect. Make sure you have read the faculty dataframe first.")

        author_ids = self.faculty_df[self.faculty_df["EID"].notna()]["EID"].tolist()
        pub_df = pd.DataFrame(AuthorRetrieval(author_ids[0]).get_documents())
        pub_df["AU-ID"] = author_ids[0]
        for id in author_ids[1:]:
            current_df = pd.DataFrame(AuthorRetrieval(id).get_documents())
            current_df["AU-ID"] = id
            pub_df = pd.concat([pub_df, current_df], ignore_index=True)

        pub_df["coverDate"] = pd.to_datetime(pub_df["coverDate"])
        self.pub_df = pub_df
        if save:
            pub_df.to_csv("pub_df.csv", index=False)
        return pub_df

    def combine_data(self, threshold=95, save=True):

        def get_academic_year(date):
            if date.month >= 9:
                return f"{date.year}-{date.year + 1}"
            else:
                return f"{date.year - 1}-{date.year}"

        faculty_pub_df = pd.merge(self.pub_df, self.faculty_df, left_on=["AU-ID"], right_on=["EID"])
        faculty_pub_df = faculty_pub_df.replace(journal_exceptions)

        # fuzzy matching journal names
        mat1 = []
        mat2 = []
        p = []

        list1 = faculty_pub_df['publicationName'].tolist()
        list2 = self.journal_list['Journal'].tolist()

        # iterating through list1 to extract
        # it's closest match from list2
        for i in list1:
            mat1.append(process.extract(i, list2, limit=1))
        faculty_pub_df['journal_match'] = mat1

        # iterating through the closest matches
        # to filter out the maximum closest match
        for j in faculty_pub_df['journal_match']:
            for k in j:
                if k[1] >= threshold:
                    p.append(k[0])
            mat2.append(",".join(p))
            p = []

        # storing the resultant jouirnal matches back to dframe1
        faculty_pub_df['journal_match'] = mat2

        faculty_pub_df = pd.merge(faculty_pub_df, self.journal_list, left_on=["journal_match"], right_on=["Journal"], how="left")
        faculty_pub_df = faculty_pub_df.drop('journal_match', axis=1)

        faculty_pub_df['academic_year'] = faculty_pub_df['coverDate'].apply(get_academic_year)

        self.faculty_pub_df = faculty_pub_df
        if save:
            faculty_pub_df.to_csv("faculty_pub.csv", index=False)

        return faculty_pub_df

    def visualize(self):
        publications_count = self.faculty_pub_df.groupby(['academic_year', 'Rank']).size().unstack(fill_value=0)
        publications_count.reset_index(inplace=True)
        filtered_publications_count = publications_count[
            (publications_count['academic_year'] >= '2013-2014') &
            (publications_count['academic_year'] != '2023-2024')
        ]

        # Create a figure and a set of subplots
        fig, ax = plt.subplots()

        # Plotting the filtered bar chart using fig, ax
        filtered_publications_count.plot(kind='bar', x='academic_year', stacked=False, ax=ax, width=0.8)

        # Adding titles and labels using ax methods
        ax.set_title('Number of Publications by Rank')
        ax.set_xlabel('Academic Year')
        ax.set_ylabel('Number of Publications')
        ax.set_xticklabels(filtered_publications_count['academic_year'], rotation=45)  # Rotate the x-axis labels

        ax.legend(title='Rank', loc="upper left")
        plt.grid(linestyle="--", alpha=0.3)
        plt.tight_layout()
        plt.savefig("publication_count.pdf")
        plt.show()
