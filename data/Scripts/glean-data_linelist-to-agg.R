## Gleam data aggregator
## 2024-09-24
## Rt eval group

## Output:
## reference_data: date of event (ie ED visit)
## report_date: when the event was reported
## location as FIPS code
## count: number of events on reference_date, report_date, location

#shape = 2, scale =1/2, mean =4 

#libraries
library(dplyr)
library(ggplot2)
library(here)

# # #read data
# file.list <- dir(here::here('data/GLEAM/raw_timeseries'), full.names = TRUE) #where you have your files
# R.utils::gunzip(file.list[4])

file.list <- dir(here::here('data/GLEAM/raw_timeseries'), full.names = TRUE) #where you have your files
# df <- do.call(rbind,lapply(file.list, read.csv, row.names=NULL))

#format model output into linelist
df <- read.csv(file.list[3])
df <- df %>% 
  rename("county" = "county_full_name",
         "state"= "state_name",
         "FIPS" = "geoid")%>%
  select(date, county, state, new_Latent, FIPS)%>%
  mutate(date = as.Date(date))
df$STATEFP <- substr(df$FIPS, start=1, stop=2)

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
df.linelist$report_time_clean = 0 #No reporting delays
set.seed(1234)
df.linelist$report_time_noise = round(rgamma(nrow(df.linelist), shape=1, scale=2)) #gamma distributed
df.linelist <- df.linelist %>%
  mutate(report_date_nonoise = reference_date + report_time_clean,
         report_date_noise = reference_date + report_time_noise)

# #aggregate
# df.county <- df.linelist %>%
#   group_by(reference_date, report_date, STATEFP, FIPS)%>%
#   summarise(count = n())%>%
#   as.data.frame()

#aggregate
df.state.nonoise <- df.linelist %>%
  rename("report_date" = "report_date_nonoise")%>%
  group_by(reference_date, report_date, state, STATEFP)%>%
  summarise(count = n())%>%
  as.data.frame()%>%
  mutate(label = "leam_no_noise")

df.state.noise <- df.linelist %>%
  rename("report_date" = "report_date_noise")%>%
  group_by(reference_date, report_date, state, STATEFP)%>%
  summarise(count = n())%>%
  as.data.frame()%>%
  mutate(label = "leam_noise_reporting_delay")

# #make sure all dates have something
# df.linelist <- left_join(date, df.state)


# write.csv(df.state, paste0(here::here('data/Test data/MA'), '/MA_NoNoise.csv')) #fix this
# write.csv(df.state, paste0(here::here('data/Test data/MA'), '/MA_DelayNoise.csv')) #fix this

df1 <- df.state.nonoise %>%
  filter(report_date <= "2025-12-31")%>%
  group_by(reference_date)%>%
  summarize(nonoise = sum(count))

df2 <- df.state.noise %>%
  filter(report_date <= "2025-12-31")%>%
  group_by(reference_date)%>%
  summarize(noise = sum(count))

df0 <- full_join(df1, df2)

#visualize
Pal1 <- c("Reporting delay" = "#03ffff5c",
          #'Reporting delay' = "#f9cb9cff",
          'Perfect reporting' = 'grey')

fig1 = ggplot()+
  theme_classic(base_size = 24)+
  #geom_col(data=df0, aes(x=reorder(STUSPS, -Total, sum), y=Total))+
  geom_col(data=df0, aes(x=reference_date, y=nonoise, fill="Perfect reporting"))+
  geom_col(data=df0, aes(x=reference_date, y=noise, fill="Reporting delay"))+
  scale_fill_manual(values = Pal1, name= " ",
                     breaks=c("Reporting delay","Perfect reporting")) +
  ylab("Hospitilizations") + xlab("Date") + ggtitle("Synthetic MA data")
fig1
