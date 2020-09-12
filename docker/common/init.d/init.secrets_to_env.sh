#!/bin/bash
# Put secrets in the environnement

function export_secrets {
    local secret_folder=/run/secrets
    for f in $(ls "$secret_folder")
    do
        f_upper=$(echo $f | tr [a-z] [A-Z])
        f_val=$(cat "$secret_folder"/"$f")
        eval "$f_upper"="$f_val"
        export "$f_upper"
    done

    return 0
}
