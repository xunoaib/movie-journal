import streamlit as st
import pandas as pd

# Sample data
data = {
    "Name": ["Alice", "Bob", "Charlie"],
    "Age": [25, 30, 35],
    "City": ["New York", "London", "Paris"]
}

# Render using pandas DataFrame
df = pd.DataFrame(data)
st.table(df)  # Static table
# or
st.dataframe(df)  # Interactive (sortable, scrollable) table
