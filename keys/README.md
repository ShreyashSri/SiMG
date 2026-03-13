# Keys
Generate before running:
  openssl ecparam -name prime256v1 -genkey -noout -out private.pem
  openssl ec -in private.pem -pubout -out public.pem

NEVER commit private.pem
