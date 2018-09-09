#reddmeet.com - meet redditors

This is a simple friends/meetup/dating app for Reddit users, written 
in Django.

See it live: https://reddmeet.com (you need a reddit account to sign in)

##What it does

The site matches redditors according to the subreddits they belong to. 
Additionally, users can be filtered by location, gender, etc.

However, the main idea is to *match people anonymously by the subreddits 
they are active in*. The post history gives a good idea about how a person 
thinks and acts in an anonymous environment.

Redditors can quickly and anonymously sign up with their reddit account.



##Setup database

$ sudo -u postgres psql
CREATE DATABASE dtr5 ;
CREATE USER redddate WITH ENCRYPTED PASSWORD 'plaplapla' ;
GRANT ALL PRIVILEGES ON DATABASE dtr5 TO redddate ;
\q
$ psql -U redddate dtr5 < 2018-08-25.psql
