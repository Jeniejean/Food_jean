import pandas as pd
import streamlit as st
import plotly.express as px
from pinotdb import connect
from datetime import datetime

# Set Streamlit to wide mode
st.set_page_config(layout="wide")

# Connect to Pinot
conn = connect(host='47.128.230.83', port=8099, path='/query/sql', scheme='http')
curs = conn.cursor()

# Streamlit App Layout
st.title("Jean Restaurant Dashboard")

# Show the last update time
now = datetime.now()
dt_string = now.strftime("%d %B %Y %H:%M:%S")
st.write(f"Last update: {dt_string}")

# Sidebar Filters
st.sidebar.markdown("### Filters")
# Gender Filter
query_gender = """
SELECT DISTINCT GENDER
FROM 5Food
"""
curs.execute(query_gender)
gender_options = [row[0] for row in curs]
selected_genders = st.sidebar.multiselect(
    "Select Genders to Display",
    options=gender_options,
    default=gender_options
)

# Region Filter
query_region = """
SELECT DISTINCT REGIONID
FROM 5Food
"""
curs.execute(query_region)
region_options = [row[0] for row in curs]
selected_regions = st.sidebar.multiselect(
    "Select Regions to Display",
    options=region_options,
    default=region_options
)

# Query 1: Distribution of Foods
query1 = """
SELECT FOOD, COUNT(*) as Count
FROM 5Food
GROUP BY FOOD
ORDER BY Count DESC
"""
curs.execute(query1)
df_foods = pd.DataFrame(curs, columns=[item[0] for item in curs.description])

# Debugging: Check the columns of the DataFrame
print("Columns in df_foods:", df_foods.columns)

# Query 3: Total View Time by Gender
query3 = f"""
SELECT GENDER, SUM(CAST(VIEWTIME AS LONG)) as TotalViewTime
FROM 5Food
WHERE GENDER IN ({', '.join("'" + g + "'" for g in selected_genders)})
GROUP BY GENDER
"""
curs.execute(query3)
df_viewtime_gender = pd.DataFrame(curs, columns=[item[0] for item in curs.description])

# Query 2: Food Distribution by Gender
query2 = f"""
SELECT GENDER, FOOD, COUNT(*) as Count
FROM 5Food
WHERE GENDER IN ({', '.join("'" + g + "'" for g in selected_genders)})
GROUP BY GENDER, FOOD
ORDER BY GENDER, Count DESC
"""
curs.execute(query2)
df_food_gender = pd.DataFrame(curs, columns=[item[0] for item in curs.description])

# Debugging: Check the columns of df_food_gender
print("Columns in df_food_gender:", df_food_gender.columns)

# Pivot table to reformat the DataFrame
df_food_gender_pivot = df_food_gender.pivot(index='GENDER', columns='FOOD', values='Count').fillna(0)

# Query 4: Total Viewtime by Region
query4 = f"""
SELECT REGIONID, SUM(CAST(VIEWTIME AS LONG)) as TotalViewTime
FROM 5Food
WHERE REGIONID IN ({', '.join("'" + str(r) + "'" for r in selected_regions)})
GROUP BY REGIONID
ORDER BY TotalViewTime DESC
"""
curs.execute(query4)
df_viewtime_region = pd.DataFrame(curs, columns=[item[0] for item in curs.description])
df_viewtime_region_filtered = df_viewtime_region[df_viewtime_region['REGIONID'].isin(selected_regions)]

# Create the first row layout with wider columns
col1, col2 = st.columns([3, 3])  # Adjust proportions to allocate more space

with col1:
    # Horizontal bar chart sorted by count (Graph 1)
    st.markdown("<h3 style='font-size: 20px;'>1. Distribution of Foods</h3>", unsafe_allow_html=True)
    fig1 = px.bar(
        df_foods,
        y='FOOD',
        x='Count',
        color='FOOD',
        labels={'FOOD': 'Food Type', 'Count': 'Count'},
        title='',  # Remove the title
        orientation='h',  # Horizontal bar chart
        width=900,  # Set width for the graph
        height=400  # Adjust height to minimize white space
    )
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Pie chart for total view time by gender (Graph 2)
    st.markdown("<h3 style='font-size: 20px;'>2. Total View Time by Gender</h3>", unsafe_allow_html=True)
    fig2 = px.pie(
        df_viewtime_gender,
        names='GENDER',
        values='TotalViewTime',
        title='',
        hole=0.4,  # Optional: Makes it a donut chart
        width=900,  # Set width for the graph
        height=400  # Adjust height
    )
    fig2.update_traces(textinfo='percent+label')  # Display percentages and labels in the pie chart
    fig2.update_layout(showlegend=False)  # Remove the legend
    st.plotly_chart(fig2, use_container_width=True)


# Create the second row layout
col3, col4 = st.columns([3, 3])  # Adjust proportions to allocate more space

with col3:
    # Use Plotly for interactive chart (Graph 3)
    st.markdown("<h3 style='font-size: 20px;'>3. Food Distribution by Gender</h3>", unsafe_allow_html=True)
    fig3 = px.bar(df_food_gender_pivot, barmode='stack', labels={'value': 'Count'},
                  title='',  # Remove the title
                  width=900,  # Set width for the graph
                  height=400  # Adjust height
    )
    fig3.update_traces(texttemplate=None)  # Remove numbers from the bars
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    # Use Plotly for interactive chart (Graph 4)
    st.markdown("<h3 style='font-size: 20px;'>4. Total Viewtime by Region</h3>", unsafe_allow_html=True)
    # Ensure sorting is applied in ascending order
    df_viewtime_region_sorted = df_viewtime_region_filtered.sort_values(by='TotalViewTime', ascending=True)

    # Custom formatting function for TotalViewTime
    def format_value(value):
        if value >= 1e9:
            return f"{value / 1e9:.2f}B"  # Format as billions
        elif value >= 1e6:
            return f"{value / 1e6:.2f}M"  # Format as millions
        elif value >= 1e4:
            return f"{value / 1e4:.2f}K"  # Format as ten-thousands
        else:
            return f"{value:.2f}"  # No unit, display as is

    # Apply formatting to a new column for display
    df_viewtime_region_sorted['FormattedTotalViewTime'] = df_viewtime_region_sorted['TotalViewTime'].apply(format_value)

    # Create TreeMap with formatted values
    fig4_treemap = px.treemap(
        df_viewtime_region_sorted,
        path=['REGIONID'],
        values='TotalViewTime',
        labels={'TotalViewTime': 'Total View Time', 'REGIONID': 'Region ID'},
        title='',
        width=900,
        height=400
    )

    # Display formatted values in the chart
    fig4_treemap.update_traces(
        texttemplate='%{label}<br>Total View Time: %{customdata}',
        hovertemplate='%{label}<br>Total View Time: %{customdata}',
        customdata=df_viewtime_region_sorted['FormattedTotalViewTime']
    )
    
    st.plotly_chart(fig4_treemap, use_container_width=True)
