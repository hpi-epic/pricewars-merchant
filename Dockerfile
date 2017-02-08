FROM python:3.5.2

ENV APP_HOME /merchant
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

ADD . $APP_HOME

RUN pip install -r merchant_sdk/requirements.txt

CMD ["python", "simple_competition_logic/MerchantApp.py", "--port", "5000"]
