FROM python:3.11-slim
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app
COPY --chown=user serve.py .
COPY --chown=user dist ./dist
ENV PORT=7860
EXPOSE 7860
CMD ["python", "serve.py"]
