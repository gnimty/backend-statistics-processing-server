# Statistics Processing Server


* local selenium starts
docker run -p 4445:4444 seleniarm/standalone-chromium 



# GCP 이관 시

- 1. secret.GOOGLE_CREDENTIAL 수정 (모든 큰따옴표 앞에 escape 문자 추가)
- 2. secret.DEV_ENV 수정 (COMMUNITY_HOST, GOOGLE_BUCKET_NAME)
