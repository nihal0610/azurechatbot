import openai
import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error

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
            "When the word 'type' is mentioned, always consider it as projecttype. "
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


# Step 1: Upload an Excel file
uploaded_file = st.file_uploader("Upload your Excel file to update the database:", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner("Processing..."):
        cursor = None  # Declare cursor outside the try block
        connection = None  # Declare connection outside the try block
        try:
            # Load the uploaded Excel file
            df = pd.read_excel(uploaded_file)
            date_cols = ['ProjectEnddate', 'ProjectStartdate', 'Allocation Start Date', 'Allocation End Date']
                for date_column in date_cols:
                    if date_column in df.columns:
                        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            df.columns = [col.strip().replace(" ", "").replace("/", "").replace("-", "") for col in df.columns]
            df = df.fillna("NULL")

            # Connect to the database
            connection = mysql.connector.connect(
                user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", 
                port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=True
            )
            cursor = connection.cursor()

            # Replace the 'utilisation' table
            cursor.execute("DROP TABLE IF EXISTS utilisation;")
            create_table_query = f"""
            CREATE TABLE utilisation (
                {', '.join([f'`{col}` TEXT' for col in df.columns])}
            );
            """
            cursor.execute(create_table_query)

            # Insert data into the new 'utilisation' table
            for _, row in df.iterrows():
                insert_query = f"INSERT INTO utilisation VALUES ({', '.join(['%s'] * len(row))})"
                cursor.execute(insert_query, tuple(row))
            connection.commit()
            st.success("Database updated successfully. You can now generate SQL queries.")

            # Step 2: Generate SQL queries based on the updated data
            user_prompt = st.text_area(
                "Describe the SQL query you need:",
                placeholder="e.g., Fetch customer names and emails where the country is 'USA'.",
            )

            if st.button("Generate SQL Query"):
                if user_prompt.strip():
                    with st.spinner("Generating SQL query..."):
                        try:
                            # Fetch the schema of the 'utilisation' table
                            table_name = "utilisation"
                            column_names = fetch_table_schema(cursor, table_name)
                            st.write(f"Columns in `{table_name}`: {', '.join(column_names)}")

                            # Generate SQL query using the schema
                            sql_query = generate_sql_query(user_prompt, column_names)
                            st.write(sql_query)
                            st.subheader("Generated SQL Query:")
                            st.code(sql_query, language="sql")

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
                else:
                    st.error("Please enter a description for the SQL query.")

        except Error as e:
            st.error(f"Error: {e}")
        finally:
            # Ensure cursor and connection are closed only if they were initialized
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()
else:
    st.warning("Please upload an Excel file to proceed.")

