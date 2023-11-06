from params import *
from funcs import *

faculty = Faculty()

faculty.load_faculty_info()
faculty.load_pub_info()
faculty.load_faculty_pub()
faculty.visualize()

# faculty_df = faculty.scrape_info(save=True)
# faculty.get_pubs()
# faculty.combine_data()

# faculty.retrieve_author_id(author_firstname="Mark", author_lastname="Rowe")
print("Done!")
