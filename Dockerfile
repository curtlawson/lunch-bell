FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY discover.py parse.py generate.py handler.py ./

CMD ["handler.lambda_handler"]
