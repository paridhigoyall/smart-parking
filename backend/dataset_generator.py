import pandas as pd
import random

data = []

for i in range(2000):

    CO = random.randint(20,200)
    CO2 = random.randint(350,1500)
    NO2 = random.randint(5,120)
    O2 = round(random.uniform(19.0,21.0),2)
    LPG = random.randint(5,200)
    Smoke = random.randint(5,150)
    Temp = random.randint(25,40)
    Humidity = random.randint(40,80)

    if CO < 60 and CO2 < 600 and NO2 < 25 and LPG < 30:
        status = "Safe"
    elif CO < 120 and CO2 < 1000 and NO2 < 60:
        status = "Moderate"
    else:
        status = "Unsafe"

    data.append([CO,CO2,NO2,O2,LPG,Smoke,Temp,Humidity,status])

df = pd.DataFrame(data,columns=[
"CO","CO2","NO2","O2","LPG","Smoke","Temp","Humidity","Parking_Status"
])

df.to_csv("gas_parking_dataset.csv",index=False)

print("Dataset Created Successfully")