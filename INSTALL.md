
##Setup database

$ sudo -u postgres psql
CREATE DATABASE dtr5 ;
CREATE USER redddate WITH ENCRYPTED PASSWORD 'plaplapla' ;
GRANT ALL PRIVILEGES ON DATABASE dtr5 TO redddate ;
\q
$ psql -U redddate dtr5 < 2018-08-25.psql
