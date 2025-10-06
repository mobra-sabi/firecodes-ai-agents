Nu pune cheile în arhivă.
Setează-le local rulând:
  bash tools/configure_openai_key.sh
și pune tokenul Brave în:
  printf '%s' 'BSA_...token...' > .secrets/brave.key && chmod 600 .secrets/brave.key
