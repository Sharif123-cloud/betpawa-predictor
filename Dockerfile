FROM python:3.9-slim

# System deps for Selenium, Buildozer, and Kivy
RUN apt-get update && apt-get install -y \
    wget curl git unzip zip \
    openjdk-17-jdk \
    chromium-driver chromium \
    build-essential autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev \
    python3-pip ccache \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir buildozer cython==0.29.36

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY . .

CMD ["bash"]
