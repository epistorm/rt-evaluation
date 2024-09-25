## Gleam data aggregator
## 2024-09-24
## Rt eval group

## Output:
## reference_data: date of event (ie ED visit)
## report_date: when the event was reported
## location
## count: number of events on reference_date, report_date, location

#libraries
library(dplyr)
library(ggplot2)
library(here)

# # #read data
# file.list <- dir(here::here('data/GLEAM/raw_timeseries'), full.names = TRUE) #where you have your files
# # df <- do.call(dplyr::bind_rows,lapply(file.list, read.csv)) #read in csvs
# 
# R.utils::gunzip(file.list[3])
file.list <- dir(here::here('data/GLEAM/raw_timeseries'), full.names = TRUE) #where you have your files
#shape = 2, scale =1/2, mean =4 

#format model output into linelist
df <- read.csv(file.list[3])
df <- df %>% 
  rename("county" = "county_full_name",
         "state"= "state_name")%>%
  select(date, county, state, new_Latent)%>%
  mutate(STATE = "MA",
         date = as.Date(date))

#take sample of infected population that gets hospitilized
set.seed(1234)
df$hosp_rate <- rnorm(nrow(df), 0.01, 0.0001)
df$hosp_number <- round(df$hosp_rate*df$new_Latent)

#create a date list
date <- data.frame(reference_date = seq(min(df$date),max(df$date),1))

#Create linelist data
df.linelist <- df %>%
  select(!c(hosp_rate, new_Latent))%>%
  tidyr::uncount(hosp_number)

#Add hospital delay
df.linelist$hosp_time = round(rgamma(nrow(df.linelist), 5))
df.linelist <- df.linelist%>%
  mutate(reference_date = date + hosp_time)

#Add reporting delay
df.linelist$report_time = 0 #No reporting delays
df.linelist <- df.linelist %>%
  mutate(report_date = reference_date + report_time)

#Convert to FIPS code
key <- read.csv("https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt", sep="|")%>%
  rename("county" = "COUNTYNAME")%>%
  select(county, STATE, STATEFP, COUNTYFP)
df.linelist <- left_join(df.linelist, key)

#format
df <- df%>%
  rename('reference_date'='hospitalization_date',
         'report_date' = 'reporting_date',
         'state' = 'state_name',
         'county'= 'county_full_name')%>%
  select(reference_date, report_date, state, county)%>%
  filter(if_any(everything(), ~ !is.na(.)))

#aggregate
df.county <- df.linelist %>%
  group_by(reference_date, report_date, STATEFP, COUNTYFP)%>%
  summarise(count = n())%>%
  as.data.frame()

#aggregate
df.state <- df.linelist %>%
  group_by(reference_date, report_date, state)%>%
  summarise(count = n())%>%
  as.data.frame()

#make sure all dates have something
df.linelist <- left_join(date, df.state)

write.csv(df.state, paste0(here::here('data/Test data/MA'), '/MA_NoNoise.csv')) #fix this
#write.csv(df.county, paste0(here::here('data'), '/county-agg-data.csv'))

df1 <- df1 %>%
  mutate(reference_date = as.Date(reference_date))

fig = ggplot()+
  theme_classic(base_size = 24)+
  geom_col(data=df1, aes(x=reference_date, y=count, fill=location))+
  scale_x_date(date_breaks = "1 week", date_labels = "%W")+
  ylab("ED visits") + xlab("Reference date")
fig

