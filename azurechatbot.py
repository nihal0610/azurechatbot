import openai
import streamlit as st
import pandas as pd
import pymysql
from mysql.connector import Error
import os
import mysql.connector

#cnx = mysql.connector.connect(user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=True)

# conn_str = os.getenv('MYSQLCONNSTR_genai')
# conn = mysql.connector.connect(conn_str)

 
st.title("Insights Generator")
 
# Set your OpenAI API key
api_key = st.text_input("Enter your OpenAI API key:", type="password", placeholder="sk-...")
 
# Ensure the user enters the API key
if not api_key:
    st.warning("Please enter your OpenAI API key to proceed.")
else:
    openai.api_key = api_key  # Set the user-provided API key
 
def fetch_table_schema(cursor, table_name):
    """
    Fetches the schema (column names and types) of a table from the database.
    """
    cursor.execute(f"DESCRIBE {table_name}")
    schema = cursor.fetchall()
    column_names = [col[0] for col in schema]
    return column_names
 
def generate_sql_query(user_prompt, column_names):
    """
    Generates an SQL SELECT query based on the user prompt and available column names.
    """
    try:
        # Format the column names as a string for the OpenAI model
        columns_description = ", ".join(column_names)
        schema_info = f"The table 'utilisation' has the following columns: {columns_description}."
 
        # Prompt for GPT-3.5 Turbo
        system_message = (
            "You are an expert SQL generator. "
            "You should only generate code that is supported in MySQL. "
            "Create only SQL SELECT queries based on the given description. "
            "The table always uses the name 'utilisation'. "
            "Only use the column names provided in the schema. "
            "Do not insert the SQL query as commented code. "
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{schema_info}\n\n{user_prompt}"}
        ]
 
        # Call the OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,  # Keep the response deterministic
            max_tokens=200  # Adjust depending on the expected query length
        )
 
        # Extract the SQL query from the response
        sql_query = response.choices[0].message.content.strip()
        return sql_query
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"
 
# Streamlit UI
 
st.write(
    "Choose between the below options: "
)
 
# Option to choose between different actions
action = st.radio(
    "Select an action:",
    (
        "Give prompt to EXISTING Data",
        "Compare your NEW EXCEL FILE with Existing File",
        "CHANGE the Existing Data with NEW EXCEL FILE",
    ),
)
 
if action == "Give prompt to EXISTING Data":
    # Text input for SQL query prompt
    user_prompt = st.text_area(
        "Describe the SQL query you need:",
        placeholder="e.g., Fetch customer names and emails where the country is 'USA'.",
    )
 
    if st.button("Generate SQL Query"):
        if user_prompt.strip():
            with st.spinner("Processing..."):
                try:
                    # Connect to the database
                    connection = mysql.connector.connect(user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=True)
                    cursor = connection.cursor()
 
                    # Fetch the schema of the 'utilisation' table
                    table_name = "utilisation"
                    column_names = fetch_table_schema(cursor, table_name)
                    # st.write(f"Columns in `{table_name}`: {', '.join(column_names)}")
 
                    # Generate SQL query using the schema
                    sql_query = generate_sql_query(user_prompt, column_names)
                    # st.subheader("Generated SQL Query:")
                    # st.code(sql_query, language="sql")
 
                    # Execute the generated SQL query
                    cursor.execute(sql_query)
                    result = cursor.fetchall()
                    st.subheader("Results:")
 
                    # Display the results
                    if result:
                        result_df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
                        st.dataframe(result_df)
                    else:
                        st.write("No results found.")
 
                except Error as e:
                    st.error(f"Error: {e}")
                finally:
                    cursor.close()
                    connection.close()
                    # st.write("MySQL connection is closed.")
        else:
            st.error("Please enter a description for the SQL query.")
 
elif action == "Compare your NEW EXCEL FILE with Existing File":
    # File upload for comparison
    uploaded_file = st.file_uploader("Upload your Excel file:", type=["xlsx"])
 
    if uploaded_file is not None:
        with st.spinner("Reading file..."):
            try:
                # Load the uploaded Excel file
                df = pd.read_excel(uploaded_file)
                date_cols = ['ProjectEnddate', 'ProjectStartdate', 'Allocation Start Date', 'Allocation End Date']
                for date_column in date_cols:
                    if date_column in df.columns:
                        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
 
                # Clean up column names
                df.columns = [col.strip().replace("  ", "").replace(" / ", "").replace("-", "").replace(" ", "") for col in df.columns]
                df = df.fillna("NULL")
            except Exception as e:
                st.error(f"Error reading the file: {e}")
   
    if st.button("Compare"):
        if uploaded_file is not None:
            with st.spinner("Processing..."):
                try:
                    # Connect to the database
                    connection = mysql.connector.connect(user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=False)
                    cursor = connection.cursor()
 
                    # Step 1: Drop the 'utilisation2' table if it exists
                    table_name = "utilisation2"
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                    # st.write(f"Table `{table_name}` has been dropped.")
 
                    # Step 2: Create the 'utilisation2' table
                    create_table_query = f"""
                    CREATE TABLE {table_name} (
                        {', '.join([f'`{col}` TEXT' for col in df.columns])}
                    );
                    """
                    cursor.execute(create_table_query)
                    # st.write(f"Table `{table_name}` has been created.")
 
                    # Step 3: Insert data into the 'utilisation2' table
                    for _, row in df.iterrows():
                        insert_query = f"INSERT INTO {table_name} VALUES ({', '.join(['%s'] * len(row))})"
                        cursor.execute(insert_query, tuple(row))
                    connection.commit()
                    # st.write(f"Data from the uploaded file has been inserted into `{table_name}`.")
 
                    # Set comparison column manually to AssociateID
                    comparison_column = "AssociateID"
                    st.write(f"Comparison will be performed on the basis of `{comparison_column}`.")
 
                    # Step 4: Compare 'utilisation' and 'utilisation2' in both directions
                    st.subheader("Data Comparison:")
 
                    # 4.1: Rows in `utilisation` that are not in `utilisation2`
                    query_utilisation_not_in_utilisation2 = f"""
                    SELECT * FROM utilisation
                    WHERE {comparison_column} NOT IN (
                        SELECT {comparison_column} FROM utilisation2
                    );
                    """
                    cursor.execute(query_utilisation_not_in_utilisation2)
                    differences_utilisation_to_utilisation2 = cursor.fetchall()
 
                    if differences_utilisation_to_utilisation2:
                        diff_df1 = pd.DataFrame(differences_utilisation_to_utilisation2,
                                                columns=[desc[0] for desc in cursor.description])
                        st.write(f"Rows in `Existing Data` which are not in `New Data` based on `{comparison_column}`:")
                        st.dataframe(diff_df1)
                    else:
                        st.write(f"No differences found from `Existing Data` to `New data` on `{comparison_column}`.")
 
                    # 4.2: Rows in `utilisation2` that are not in `utilisation`
                    query_utilisation2_not_in_utilisation = f"""
                    SELECT * FROM utilisation2
                    WHERE {comparison_column} NOT IN (
                        SELECT {comparison_column} FROM utilisation
                    );
                    """
                    cursor.execute(query_utilisation2_not_in_utilisation)
                    differences_utilisation2_to_utilisation = cursor.fetchall()
 
                    if differences_utilisation2_to_utilisation:
                        diff_df2 = pd.DataFrame(differences_utilisation2_to_utilisation,
                                                columns=[desc[0] for desc in cursor.description])
                        st.write(f"Rows in `New data` which are not in `Existing Data` based on `{comparison_column}`:")
                        st.dataframe(diff_df2)
                    else:
                        st.write(f"No differences found from `New data` to `Existing Data` on `{comparison_column}`.")
 
                except Error as e:
                    st.error(f"Error: {e}")
                finally:
                    cursor.close()
                    connection.close()
                    # st.write("MySQL connection is closed.")
        else:
            st.error("Please upload an Excel file.")
 
elif action == "CHANGE the Existing Data with NEW EXCEL FILE":
    # File upload for replacing the existing database
    uploaded_file = st.file_uploader("Upload your Excel file:", type=["xlsx"])
 
    if st.button("REPLACE"):
        if uploaded_file is not None:
            with st.spinner("Processing..."):
                try:
                    # Load the uploaded Excel file
                    df = pd.read_excel(uploaded_file)
                    df.columns = [col.strip().replace(" ", "").replace("/", "").replace("-", "") for col in df.columns]
                    df = df.fillna("NULL")
 
                    # Connect to the database
                    connection = mysql.connector.connect(user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=True)
                    cursor = connection.cursor()
 
                    # Replace the 'utilisation' table
                    cursor.execute(f"DROP TABLE IF EXISTS utilisation;")
                    # st.write("Existing `utilisation` table has been dropped.")
 
                    create_table_query = f"""
                    CREATE TABLE utilisation (
                        {', '.join([f'`{col}` TEXT' for col in df.columns])}
                    );
                    """
                    cursor.execute(create_table_query)
                    # st.write("New `utilisation` table has been created.")
 
                    # Insert data into the new 'utilisation' table
                    for _, row in df.iterrows():
                        insert_query = f"INSERT INTO utilisation VALUES ({', '.join(['%s'] * len(row))})"
                        cursor.execute(insert_query, tuple(row))
                    connection.commit()
                    st.write("The file has been replaced. Please navigate to first option to give prompt.")
 
                except Error as e:
                    st.error(f"Error: {e}")
                finally:
                    cursor.close()
                    connection.close()
                    # st.write("MySQL connection is closed.")
        else:
            st.error("Please upload an Excel file.")
 
