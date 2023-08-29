# Utilise l'image de Python 3.11
FROM python:3.11-slim

# Installe wget et les dépendances de Chrome
RUN apt-get update
RUN apt-get install -y wget gconf-service libasound2 libatk1.0-0 libcairo2 libcups2 libfontconfig1 libgdk-pixbuf2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libxss1 fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils

# Installe Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

RUN rm google-chrome-stable_current_amd64.deb
# Vérifie la version de Chrome
RUN echo "Chrome: " && google-chrome --version

# Installe les dépendances de Python
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copie le répertoire de travail dans le dossier /app de l'image
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .

# Exécute le script
CMD ["python", "main.py"]