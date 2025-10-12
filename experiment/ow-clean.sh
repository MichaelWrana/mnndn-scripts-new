awk -F, 'NR>1 { c=$6+0; if (c>0 && c<100) print $2 }' top-1m.csv \
| while IFS= read -r domain; do
  dir="webpage_data/$domain"
  [ -d "$dir" ] && rm -rf -- "$dir"
done

