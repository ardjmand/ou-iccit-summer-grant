import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['text.usetex'] = True
plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}'
plt.rcParams['font.family'] = 'serif'
import seaborn as sns
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import requests
import re
import time
from pybliometrics.scopus import AuthorRetrieval, AuthorSearch, ScopusSearch
from fuzzywuzzy import fuzz, process
import fuzzy_pandas as fpd

faculty_url = "https://www.ohio.edu/business/about/faculty-staff"
departments = ["Analytics and Information Systems Faculty",
               "Finance Faculty",
               "Accounting Faculty",
               "Management Faculty",
               "Marketing Faculty",
               "Sports Administration Faculty"]
name_exceptions = {'Elizabeth "Liz" Wanless': "Liz Wanless"}
journal_exceptions = {"MIS Quarterly: Management Information Systems": "MIS Quarterly",
                      "Applied Soft Computing Journal": "Applied Soft Computing",
                      "Advances in Accounting Education: Teaching and Curriculum Innovations": "Advances in Accounting Education"}
