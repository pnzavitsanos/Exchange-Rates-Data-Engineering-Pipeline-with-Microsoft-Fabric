import os
import requests
import pandas as pd
import psycopg


# ---------------- EXTRACT ----------------

url = "https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,CHF"

response = requests.get(url, timeout = 10)      # protected against indefinite connection time
response.raise_for_status()                     #inspect the request status (200, 404, 500) - raise an exception 
#print(response)

data = response.json()


# ---------------- TRANSFORM ----------------

df = pd.DataFrame(
    data["rates"].items(),
    columns=["currency", "rate"]
)

df["date"] = data["date"]
df["base_currency"] = data["base"]
df["amount"] = data["amount"]

df["date"] = pd.to_datetime(df["date"])

#df.loc[0, "rate"] = -1

# ---------------- VALIDATE ----------------

missing_values = df.isna().sum().sum()

if missing_values == 0 and (df["rate"] > 0).all():
    print("Validation passed")
else:
   # print("Validation failed")
   raise ValueError("Validation failed")


# ---------------- INSPECT ----------------

print(df)
print(df.dtypes)


# ---------------- CONNECT TO POSTGRESQL ----------------

connection = psycopg.connect(
    dbname="exchange_data",
    user="postgres",
    password=os.environ.get("PGPASSWORD", ""),    # read from an environment variable instead of hard-coding it
    host="localhost",
    port="5432"
)

cursor = connection.cursor()                #create the cursor 


print("Connected to PostgreSQL")


# ---------------- LOAD ----------------

for _, row in df.iterrows():

    cursor.execute(                                             #execute SQL commands with cursor / synchronize the pipeline with incoming source data
        """
        INSERT INTO exchange_rates
        (currency, rate, date, base_currency, amount)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (date, base_currency, currency)
        DO UPDATE SET                                           
             rate = EXCLUDED.rate,
            amount = EXCLUDED.amount;
        """,
        (
            row["currency"],
            row["rate"],
            row["date"],
            row["base_currency"],
            row["amount"]
        )
    )

connection.commit()

cursor.execute("SELECT COUNT(*) " \
"FROM exchange_rates;")
print(cursor.fetchone())


cursor.execute("""
    SELECT currency, rate
    FROM exchange_rates;
""")
#print(cursor.fetchall())

cursor.execute("""SELECT date, COUNT(*)
FROM exchange_rates
GROUP BY date;""")
print(cursor.fetchall())

print("Data loaded successfully")