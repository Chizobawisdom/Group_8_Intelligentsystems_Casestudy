FROM mariadb:11.8.8
# Copy the SQL files directly into the initialization folder
COPY ./schema/schema.sql /docker-entrypoint-initdb.d/1-schema.sql
COPY ./schema/data.sql /docker-entrypoint-initdb.d/2-data.sql