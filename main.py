import streamlit as st
import pandas as pd
from pathlib import Path
import xlrd
import sys
import openai as client
import time
import altair as alt


#-----------------------------------------------------------------
# Step 1: Get OpenAI API key e setup of global variables
#-----------------------------------------------------------------
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client.api_key = OPENAI_API_KEY

# Set title and width that appears on the Browser's tab bar.
st.set_page_config(
    page_title='HESRI 2 - Country profile',
    layout="wide",
)
st.markdown("""<style> .big-font {    font-size:300px !important;} </style>""", unsafe_allow_html=True)

# Display image as heading
#st.image(Path(__file__).parent/'img/bars.png')
st.image(Path(__file__).parent/'img/logomain.jpg', width=600)
st.title(":orange[HESRI2 tool for Country Assessment...]")
c1, c2 =  st.columns([2,1])

#-----------------------------------------------------------------
# Step 2: Loading from data files
#-----------------------------------------------------------------
df_countries =   pd.read_excel(Path(__file__).parent/'data/countries_WHO_Euro.xls') 
df_stratifiers = pd.read_excel(Path(__file__).parent/'data/hesri2_stratifiers.xlsx') 
life_course = ['Children', 'Young adults', 'Working age', 'Elderly', 'All ages']
life_course_stages = []
selected_stage = None

df_hesri2_filtered = pd.read_csv(Path(__file__).parent/'data/hesri2_filtered_mostrecent.csv', low_memory=False)    
df_hesri2_ai_filtered = pd.read_csv(Path(__file__).parent/'data/hesri2_ai_filtered.csv', low_memory=False)    


#-----------------------------------------------------------------
# Step 3:  difinition of a function to draw data 
#-----------------------------------------------------------------
@st.cache_data
def convert_for_download(df):
    return df.to_csv().encode("utf-8")

def draw_chart (df, df2, container): 

    chart = alt.Chart(df).mark_line(point=True).encode(
                x=alt.X('year:Q', sort='ascending', axis=alt.Axis(format='d')),   
                y='estimate:Q',
                color= 'subgroup',
                tooltip=['year', 'estimate', 'setting_x', 'indicator_name_x', 'dimension']
            ).properties().interactive()
      
    with container:
        st.dataframe(df2) 
        #to prepare data for download           
        csv = convert_for_download(df_pivot)
        
        #to visualize download button
        filename = "data" + selected_country + "-" + row.indicator_name_x + row.dimension + ".csv"
        st.download_button(
            label="Download CSV for further analysis",
            data=csv,
            file_name= filename,
            mime="text/csv",
            icon=":material/download:",                
        )
                
        st.altair_chart(chart, use_container_width=True)       
        st.subheader("", divider="grey")        
        
        
    return

#-----------------------------------------------------------------
# Step 4: Get input from user to filter data
#-----------------------------------------------------------------
#country and life stage selection
selected_country= c1.selectbox(
    ''':green[*Which WHO/Europe country would you like to select?*]''', df_countries['Countries.short_name'], index=None)

selected_stage = c1.selectbox(
    ''':green[*Which life-course stage would you like to select?*]''', life_course, index=None)
st.subheader ('', divider="red")

df_country_selected = df_countries[df_countries['Countries.short_name'] == selected_country]       

AIon = c2.toggle("Activate AI comments")

if (selected_stage != None):
    life_course_stages.append(selected_stage)
else:
    life_course_stages = life_course

#selecting most recent data from the main dataframe and for the selected country
df_hesri2_ready= pd.merge(df_hesri2_filtered, df_country_selected, on=['iso3'], how='inner')
df_hesri2_ai_filtered = pd.merge(df_hesri2_ai_filtered, df_country_selected, on=['iso3'], how='inner')

if (selected_country != None):
    for item in life_course_stages:
        a = df_hesri2_ready[df_hesri2_ready['life-course stage'] == item]
        a = a[['Category', 'indicator_name_x', 'setting_x', 'year', 'dimension', 'subgroup', 'estimate']]
                
        c1.title ("Country: "+selected_country+" - Life stage: "+item)
        c1.subheader (item+ ": indicators selected", divider="green")
        
        #to prepare dataframe for feeding AI
        ai = df_hesri2_ai_filtered[df_hesri2_ai_filtered['life-course stage'] == item]
        ai = ai[['Category', 'indicator_name_x', 'setting_x', 'year', 'dimension', 'subgroup', 'estimate']]
                        
        grouped = ai.drop_duplicates (subset=['Category', 'indicator_name_x', 'dimension'])
        grouped = grouped[['Category', 'indicator_name_x', 'dimension']]
        c1.table (grouped)
                    
        #iteration on indicators for a life course stage
        for row in grouped.itertuples():
            df_to_pass = ai[((ai['indicator_name_x'] == row.indicator_name_x) & (ai['dimension'] == row.dimension) )]
            df_to_pass = df_to_pass.sort_values(by=['year'])         
            #df_pivot = pd.pivot_table(df_to_pass, values="estimate", index=['indicator_name_x', 'dimension', 'year'], columns =['subgroup'])
            df_pivot = pd.pivot_table(df_to_pass, values="estimate", index=['year'], columns =['subgroup'])
            c1.write(f'<p style="font-size:26px; color:green;">{"Category: "+row.Category  }</p>', unsafe_allow_html=True)
            c1.write(f'<p style="font-size:26px; color:green;">{"Indicator: " +row.indicator_name_x}</p>', unsafe_allow_html=True)
            c1.write(f'<p style="font-size:26px; color:green;">{"Dimension: "+row.dimension}</p>', unsafe_allow_html=True)
            options = df_to_pass['subgroup'].unique()
            
            if (len(df_pivot) != 0): 
                draw_chart (df_to_pass, df_pivot, c1)                            
            else:
                c1.write ("No data for such an indicator/dimension")
                c1.subheader ('',divider="grey")
                                        
        if AIon:
            c1.write("Data analysis with AI in progress... Country: "+ selected_country + " Life course stage:" + item)                  
            prompt0 = selected_country + "\n" + item + "\n"+ ai.to_string()
            print ("AI data to feed prompt")
            
            messages = []
            #AI content generation
            with st.spinner(""):
                
                #first prompt related to data analysis
                input ="You are an experienced data scientist. Use the following data for country " + selected_country + " and provide comment on trends and relations between indicators collected. Elaborate a concise report highlighting differences for males and females, focus on life-course stage" + item + " and analyse groups with different education or income and trends over time" + prompt0 + " Do not add introductions or conclusions. No AI disclaimers or pleasantries. Use bullet points, titles and text."
                
                messages.append({"role": "user", "content": input})
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages
                    )
                
            print ("Prompt narrative in generation analysis")
            assistant_reply = response.choices[0].message.content
            c1.write ("****** Data analysis report:")
            c1.write (assistant_reply)
            c1.write ("****************************************************************")

sys.exit(0)