#!/bin/sh
# check secrets and set them if needed

if test -z "$ENV"
then
    echo "$ENV is not set. Don't forget to 'export ENV' to a sensible value before invoking the script"
    exit 1
fi
wd="secrets/$ENV"
if test ! -d "$wd"
then
    echo "$wd" folder does not exists. Are you executing the script in the project root folder?
    exit 1
fi
cd "$wd"

secrets_file="secrets.txt"
if test ! -f "$secrets_file"
then
    echo "$secrets_file" does not exists. No secret to set...
    exit 0
fi

readarray -t secrets < "$secrets_file"

for secret in ${secrets[@]}
do
    file="${secret}.txt"
    if test ! -f "$file"
    then
        read -r -p "set secret $secret: " secret_value
        echo "$secret_value" > "$file"
    # else
    #     echo "$file already exists"
    fi
done

echo "Secrets are set. If you need to edit those, you can do so in the newly" \
    "related files created in the secrets folder"

exit 0
