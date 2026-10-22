// One pipeline per bank. Each bank uses its own download procedure:
// rsync, wget, NCBI datasets API, Aspera, post-processing (makeblastdb)...

params.source_url = 'ftp://ftp.ncbi.nlm.nih.gov/refseq/release/complete/'
params.bank = 'refseq'
params.version = 'unknown'
params.banks_dir = '/data/dbs'

process download {
    // The bank-specific sync script lives here
    output:
    path 'download', emit: files

    script:
    """
    mkdir -p download
    wget -r -np -nd -A '*.genomic.fna.gz' ${params.source_url} -P download/
    """
}

process checksum {
    input:
    path files
    output:
    path 'checksums.txt'
    script:
    """
    md5sum ${files} > checksums.txt
    """
}

process install {
    // Atomic switch to the "current" directory
    input:
    path files
    output:
    stdout
    script:
    """
    dest=\${params.banks_dir}/\${params.bank}/\${params.version}
    mkdir -p \$dest.tmp
    mv ${files} \$dest.tmp/
    rm -rf \$dest.tmp/../\${params.version}.tmp.old 2>/dev/null || true
    [ -d \${params.banks_dir}/\${params.bank}/\${params.version} ] && \
      mv \${params.banks_dir}/\${params.bank}/\${params.version} \$dest.tmp.old || true
    mv \$dest.tmp \$dest
    echo "installed in \$dest"
    """
}

workflow {
    download()
    checksum(download.outputs.files)
    install(checksum.output)
}