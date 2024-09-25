library(tidyverse)

create_snapshot <- function(data, vintage_date) {
  # Filter the data to include only rows where report_date is on or before the vintage_date
  snapshot <- data %>%
    dplyr::filter(report_date <= vintage_date) %>%
    group_by(county, state, label, date) %>%
    summarise(total_count = sum(count), .groups = 'drop')
  
  return(snapshot)
}