import streamlit as st
import pandas as pd
from pathlib import Path
import xlrd
import sys
import openai as client
import time


#-----------------------------------------------------------------
# Step 1: Get OpenAI API key
#-----------------------------------------------------------------
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client.api_key = OPENAI_API_KEY

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='HESRI 2 - Country profile',
    layout="wide",
)

df_hesri2 = pd.read_csv(Path(__file__).parent/'data/hesri2.csv', low_memory=False)    
df_countries =   pd.read_excel(Path(__file__).parent/'data/countries_WHO_Euro.xls') 
df_stratifiers = pd.read_excel(Path(__file__).parent/'data/hesri2_stratifiers.xlsx') 
life_course = ['Children', 'Young adults', 'Working age', 'Elderly', 'All ages']


#filtering the dataset based on indicator code
#df_hesri2 = df_hesri2[df_hesri2['indicator_abbr'] == "s1_007a"].iloc[:, :]

#most recent data by country, indicator, dimension
grouped = df_hesri2.groupby(['setting', 'indicator_abbr', 'dimension' ]).agg({ 'year': 'max', })  

#selecting most recent data from the main dataframe
df_mostrecent = pd.merge(df_hesri2, grouped, on=['setting', 'indicator_abbr', 'dimension', 'year'], how='inner')

#selecting indicators from hesri2_stratifiers file countryprofile=='TRUE'
df_indicators_selected = df_stratifiers[(df_stratifiers['countryprofile'] == True)]

#dataframe for manual analysis
df_hesri2_filtered = pd.merge(df_mostrecent, df_indicators_selected, on =['indicator_abbr', 'dimension'], how='inner')

#dataframe for AI submission
df_hesri2_ai_filtered = pd.merge(df_hesri2, df_indicators_selected, on =['indicator_abbr', 'dimension'], how='inner')

st.title(":green[HESRI2 tool for Country Assessment]")
st.header("... a companion to HESRI online ATLAS ")

c1, c2 =  st.columns(2)

#country selection
selected_country= c1.selectbox(
    ''':green[*Which WHO/Europe country would you like to select?*]''', df_countries['Countries.short_name'], index=None)

df_country_selected = df_countries[df_countries['Countries.short_name'] == selected_country]       

#selecting most recent data from the main dataframe and for the selected country
df_hesri2_ready= pd.merge(df_hesri2_filtered, df_country_selected, on=['iso3'], how='inner')

c = st.columns(1)
st.write ("Life course stages indicators, most recent data by available dimensions for country: ", selected_country)

if (selected_country != None):
    for item in life_course:
        a = df_hesri2_ready[df_hesri2_ready['life-course stage'] == item]
        a = a[['Category', 'indicator_name_x', 'setting_x', 'year', 'dimension', 'subgroup', 'estimate']]
                
        st.subheader (item)
        
        @st.cache_data
        def convert_for_download(df):
            return df.to_csv().encode("utf-8")
        
        csv = convert_for_download(a)
        
        filename = "data" + selected_country + "-" + item + ".csv"
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name= filename,
            mime="text/csv",
            icon=":material/download:",
            
        )
        
        st.table (a)        
        
        st.write ("AI Generation ***************")
        time.sleep(1)
        prompt0 = selected_country + "\n" + item + "\n"+ a.to_string()
        
        messages = []

        with st.spinner("Data analysis in progress... Country: "+ selected_country):
            
            #first prompt related to data analysis
            input ="You are an experienced data scientist. Use the following data for country " + selected_country + " and provide comment on trends and relations between indicators collected. Elaborate a concise report highlighting differences for males and females, focus on life-course stage" + item + " and analyse groups with different education or income and trends over time" + prompt0 + " Do not add introductions or conclusions. No AI disclaimers or pleasantries. Use bullet points, titles and text."
            
            messages.append({"role": "user", "content": input})
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages
                )
            
        print ("Prompt narrative in generation analysis")
        assistant_reply = response.choices[0].message.content
        st.write ("****** Data analysis report:")
        st.write (assistant_reply)
        st.write ("****************************************************************")


sys.exit(0)    
   
# Second prompt for elaboration
input2 = "You are a senior political advisor and you have to prepare a report with actionable points related to public health goods and services plan to be provided in your country. The country to focus is "    + selected_country + "." + selected_country + """ has a several laws and regulation related to health sector. Collect them for your reference. Your scope is to create a document with a different vision of health. Health is both a foundation and a goal of well-being economies. Health systems are not only economic sectors in their own right—employing millions and generating social value—but also key enablers of human development, social cohesion, and environmental sustainability. The vision will strengthen national capacities to generate, govern, and use health-related data to inform policies that promote equitable, resilient, and prosperous societies. 
The vision works on 4 well-being capitals: Human well-being, Social well-being, Planetary well-being, Economic well-being. Human well-being is important because people's health and their subjective well-being are closely linked; both are drivers of economic prosperity, social mobility and cohesion. Human well-being is measured by indicators like: Healthy life expectancy, Mental health and well‑being, Ability to carry out daily activities free from illness, Universal Health Coverage, Quality and non‑discriminatory health & social care, Universal policies for housing food and fuel security, Early childhood development, Lifelong learning and literacy, Safe, orderly & regular migration. 
Social well-being is represented by Trust, participation and social cohesion make significant contributions to mental and physical health and well-being, and are vital to building fair, peaceful, and resilient societies. Social well-being is measured by Living in safety and free from violence, Sense of belonging (“Mattering”), Social cohesion and embracing diversity, Perceived ability to influence politics and decisions, Social support and protection, Building trust in others and in institutions, Public spending on communities, Participation in volunteering.
Planetary well-being is a key determinant of physical, mental and social well-being for current and future generations. It is also essential for economic prosperity. Environmental damage has significant negative impacts on well-being and prosperity. Planetary well-being is measured by Good air and water quality, Healthy and sustainable living environment, Sustainable public transport and active travel, Access to safe green space, Stable climate Biodiversity and natural capital, Circular economy and green technology.
Economic well-being impacts physical and mental health and well-being and is essential to ensure that people have a sustainable income, as well as assets, so that they can prosper and participate in society. It's measured by Living wage, Universal social protection through the life‑course, Decent and psychologically safe work, Gender‑responsive employment, Social dialogue and collective bargaining, Economic cohesion and balanced development.

Potential actions and activities carried by stakeholders to promote well-being are also mentioned in the WHO publications 'Health in the well-being economy' WHO/EURO:2023-7144-46910-68439 and in 'Deep dives on the well-being economy showcasing the experiences of Finland, Iceland, Scotland and Wales: summary of key findings' WHO/EURO:2023-7033-46799-68216. Please take inspiration by these publication whilst you prepare your report.
Elaborate on the data given previously for """ + selected_country + """ around the 4 well-being capitals and indicators (where possible disaggregated by sex, gender, and age), if it's needed collect additional data and describe what are the key points to be considered for planning goods and services to promote the 4 well-being capitals.
Provide a 5 page long report with actions for each well-being capital with content reference and data sources. Reason your points in relation to health laws and policies and data provided by highlighting data and relations among indicators. 
Highlight data improvements that could be depending by the implementation of a law, expand key actions for each well-being capital by reasoning the choice with your comments and recommendations. At the end of your report make a summary table of recommendations, with well-being capitals as rows and key actions, legal/policy basis, expected impact as columns. 
Do not add introductions or conclusions. No AI disclaimers or pleasantries. Use bullet points, titles and text."""

messages.append({"role": "assistant", "content": assistant_reply})
messages.append({"role": "user", "content": input2})

with st.spinner("Narrative in progress... Country: "+ selected_country):
    print (messages)           
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
        )
    assistant_reply = response.choices[0].message.content
    
st.write ("****** AI report:\n")
st.write (assistant_reply)
 