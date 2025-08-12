# Overview

The fastq_to_json.py script is designed to be adaptable to most inputs, this also causes it to be complex. There are typically patterns to how fastq files are named, otherwise it would be impossible to differentiate germline vs tumor, dna vs rna, genome vs exome, etc - unless external tracking is available, but what is tracked and the formats will vary significantly.

The fastqs we generate at TGen typically follow this naming convention:
STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY_FLOWCELL_BARCODE_LANE_R1_000.fastq.gz

If your fastqs are very simply named without any identifiable patterns, then I'd recommend renaming them based on whatever external metadata you have.

Most data falls into either tumor or normal (also known as germline or constitutional), then also broken down into genome, exome, or rna. Tumor vs normal is typically easy to assign, but assigning genome, exome, or rna correctly can be a bit more challenging. For exomes, using the right assayCode is critical for correct data processing - this is because we use the assayCode to automatically decide on what capture regions to process and filter to. For genomes we don't care too much about the specific assayCode other than simply for tracking purposes. For RNA the assayCode also doesn't matter too much, but here we typically care about the read orientation, strand type, and strand direction. Read orientation is almost always "inward", strand type is typically "stranded" or "unstranded", and strand direction is "forward", "reverse", or "notapplicable" in the case of "unstranded" strand types. Adapting to these different data types we use the following cli options:  


`-a, --assay` assigns the defined assay code to all detected fastqs  
`-gp, --glprep` assigns the defined glprep to all detected fastqs, typically Genome, Capture, or RNA  
`-gt, --gltype` assigns the defined gltype to all detected fastqs, typically Genome, Exome, or RNA  
`-sg, --subgroup` assigns the defined subgroup to all detected fastqs, typically tumor or constitutional  
All of the above options also have a more advanced Pattern option, such as `-ap, --assayPattern` which accepts a comma separated set of key value pairs, where the key would be an identifying glob pattern in the fastq name and the value is what to assign. For example `--assayPattern KHS6U="*_exome*",TSMRU="*_RNA_*"`.  


We also like to extensively define RG tags as they relate to the samtools SAM/BAM spec, plus some additional values to define the study and a sample name/id (can be the same as the RGSM tag). So the other dynamic options relate to defining these values. For example, the CN tag is defined as the center that produced the sequencing data, more than likely the data you are processing is all from one center. So we can use `-c, --center` to define a global value for center, e.g. `--center TGen`. We have the following options available:  

`-s, --study` Name of the study, e.g. MMRF, C4RCD, TCL, etc  
`-c, --center` Center the data originates from, defaults to TGen  
`-m, --model` Platform model the data is from, defaults to NovaSeq6000  
`-sn, --sampleName` If defined, sampleName of all fastq files  
`-sm, --rgsm` If defined, rgsm of all fastq files  
`-lb, --rglb` If defined, rglb of all fastq files  


Again, some of these options have more advanced versions available, but in this case we ask what fields should be used to assign the value. A field is any string of characters surrounded by an underscore. For example, if we want the first 3 fields plus field 5 as our rgsm then we would use `--rgsmField 1-3,5` or `--rgsmField 1,2,3,5`. Here are the options that have an Field version:  

`-snf, --sampleNameField` If defined, the specific fields or range of fields to use for sampleName  
`-smf, --rgsmField` If defined, the specific fields or range of fields to use for rgsm  
`-lbf, --rglbField` If defined, the specific fields or range of fields to use for rglb  

Finally, the remaining the cli options are to define some patient level data or adjust how the pipeline runs. For example if we know the sex of the patient/sample, then we can give that as an input `-S, --sex`. You might have also noticed that only a few RG tags are configurable via the command line. This is because the script will attempt to grab this information from the fastq for us unless we use the `-d, --dummy` option which simply populates most fields with dummy values. Part of the way the pipeline attempts to speed up alignment is that we split the fastqs into chunks and process that fixed chunk size in parallel. In order to know how many chunks to make we typically expect the numberOfReads to be defined. The fastq_to_json script will calculate this, but it can take some time to process - we can skip this computation via `-nc, --noCompute`, which can be particularly helpful when first figuring out what command line options we want to use before overall scripting the process. The last option of importance is `-t, --template` which is used to configure that tasks we want to enable for the pipeline. This accepts a json just like the one we are attempting to generate here, so we can use the json from an entirely different project/submission if we like the tasks that were enabled in that json. In this gist there is a template json that is mostly configured already for the most commonly ran configuration, feel free to use this to get started and make edits as you see fit. Also feel free to contact me with questions on configuring this.

## Usage Examples

### Example 1 - Short fastq names
Sample1_exomeGermline_S1_L001_R1_001.fastq.gz  
Sample1_exomeTumor_S1_L001_R1_001.fastq.gz  
Sample1_RNA_S1_L001_R1_001.fastq.gz  

We can see that there is a clear sample field, followed by a some combined information telling us that this is an exome from either a normal(germline) or tumor OR we have RNA data. For the exome we don't know the capture kit that was used, but hopefully this is known in some external tracking. Additionally, the RNA fastq doesn't appear to indicate whether it is normal or tumor data. In this case I know that the exome is Agilent SureSelect Human All Exon V6 + UTR. Internally this maps to the S6U short assay code - we support most common kits, but if we knew that this was custom capture then it's highly recommended to contact me (bturner@tgen.org) - or generally jetstream@tgen.org.  

To define the assayCodes for this set of data I would use `-ap` or `--assayPattern` as follows `-ap KHS6U="*_exome*",TSMRU="*_RNA_*"` - Note that by convention the assay codes we use are a 5 character string, but the pipeline typically only cares about the last 3 characters, so we can use any alphanumeric character to populate the first 2, I typically use "KH", but "UU" or "XX" are also common. For the RNA, not many details were known here, so we could use "UUUUU" for the assay code, or any 5 character string. I used "TSMRU" since it is common within our internal data.  

Next to define glprep and gltype, I would use `--glprepPattern Capture="*_exome*","RNA=*_RNA_*"` and `--gltypePattern Exome="*_exome*",RNA="*_RNA_*"` - these relatively easy to indentify in the input. And for subgroup assignment I would use `--subgroupPattern "Constitutional=*Germline*,Tumor=*Tumor*,Tumor=*_RNA_*"`  

Finally, for sampleName, rgsm, and rglb, we don't have that many fields to work with, but the first two fields cause us to differentiate enough from each other so we can simply use the first two fields for all of these assignments: `--sampleNameField 1-2`, `--rgsmField 1-2`, `--rglbField 1-2` - this isn't typically recommended but the naming convention used here doesn't leave room for the possibility of additonal sequencing at a later date.  

The overall command line for this set of data would look something like this:
```console
python3 fastq_to_json.py \
-n EXAMPLE1 \ # Name of the submission and json
-i /path/to/input/data \ # Input path/prefix to where the fastqs are stored
-ap KHS6U="*_exome*",TSMRU="*_RNA_*" \ # Assigning assayCodes based on naming features in the fastqs
-gpp Capture="*_exome*","RNA=*_RNA_*" \ # Assigning glprep based on naming features in the fastqs
-gtp Exome="*_exome*",RNA="*_RNA_*" \ # Assigning gltype based on naming features in the fastqs
-sgp "Constitutional=*Germline*,Tumor=*Tumor*,Tumor=*_RNA_*" \ # Assigning subgroup . . .
-smf 1-2 \ # Fields to use for defining rgsm
-snf 1-2 \ # Fields to use for defining sampleName
-lbf 1-2 \ # Fields to use for defining rglb
-p tempe@v1.2.1 \ # Pipeline and version to submit to
-s STUDY \ # Study name
-t template.json # Path to a template json to use for defining tasks
```

### Example 2 - Unknown gltype

/path/to/GermlineDNA/C083-000078_WF00079701_h092334-01D-01L_GermlineDNA_R1_001.fastq.gz  
/path/to/TumorDNA/C083-000078_WF00079701_I000315-01D-01L_TumorDNA_R1_001.fastq.gz  
/path/to/TumorRNA/C083-000078_WF00079701_I000315-01R-01L_TumorRNA_R1_001.fastq.gz  

This has more fields to work with than the first example, but we also have '-' separators as well as '\_'. We also don't necessarily know if the DNA data is from an exome or a genome, it's likely safe to assume that this is from a genome - the only impact here is how the variants are filtered and what regions are included in copy number analysis. Additionally, the fastqs are in separate directories, with recent updates the `-i` argument accepts multiple space delimited paths - this makes it easy to use with globbing, e.g. we will want to use `-i /path/to/*/` - if multiple samples are in the same directory, you might want to consider using `-i /path/to/*/C030-000078` since `-i` is essentially defining the prefix for all fastq paths. I'd recommend taking a look at the break down for why specific options are used in Example 1, overall this is the command line I would use for this data:

```console
python3 fastq_to_json.py \
-n C083-000078 \ # Name of the submission and json
-i /path/to/*/C030-000078 \ # Input path/prefix to where the fastqs are stored
-ap KHWGS="*DNA_*",TSMRU="*RNA_*" \ # Assigning assayCodes based on naming features in the fastqs
-gpp Genome="*DNA_*","RNA=*RNA_*" \ # Assigning glprep based on naming features in the fastqs
-gtp Genome="*DNA_*",RNA="*RNA_*" \ # Assigning gltype based on naming features in the fastqs
-sgp "Constitutional=*_Germline*,Tumor=*_Tumor*" \ # Assigning subgroup . . .
-smf 1-4 \ # Yields C083-000078_WF00079701_h092334-01D-01L_GermlineDNA
-snf 1-4 \ # Yields C083-000078_WF00079701_h092334-01D-01L_GermlineDNA
-lbf 3 \ # Yields h092334-01D-01L
-p tempe@v1.2.1 \ # Pipeline and version to submit to
-s STUDY \ # Study name
-t template.json # Path to a template json to use for defining tasks
```

### Example 3 - Public SRA data

SRR5815985_R1.fastq.gz

When downloading public data from SRA the naming scheme is typically very short and we don't have practically any fields to operate on, so we need to make use of the `--dummy` option. This only works well if you have a simple use case, e.g. you are simply attempting to process some standalone germline/constitutional DNA data or perhaps some standalone RNA data. This also means that the command line becomes a bit more simple since we don't need to defined specific identifiable features. If you are using public data and would like to run, for example, tumor vs normal data, then you will need to rename the fastqs accordingly.

For this scenario I would use the following command line:
```console
python3 fastq_to_json.py \
  --name SRR5815985 \
  --input ${PWD}/SRR5815985 \
  --assay TSMRU \
  --glprep RNA \
  --gltype RNA \
  --subgroup Tumor \
  --pipeline tempe@v1.2.1 \
  --dummy \
  --noCompute \
  --template template.json
```

### Example 4 - Follows TGen Naming Convention

AIPECGS_49601_2_PB_Whole_C1_K1ID2_L85409_HCTMVDSX7_ATTGCGTG_L001_R1_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_K1ID2_L85409_HCTMVDSX7_ATTGCGTG_L001_R2_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_K1ID2_L85411_HCWJ5DSX7_CTGCACTT_L001_R1_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_K1ID2_L85411_HCWJ5DSX7_CTGCACTT_L001_R2_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_K1RIB_L85413_HCWJ5DSX7_CGGACAAC_L001_R1_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_K1RIB_L85413_HCWJ5DSX7_CGGACAAC_L001_R2_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_WGWGS_L86820_22GM2CLT3_CCTATGCC_L007_R1_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_WGWGS_L86820_22GM2CLT3_CCTATGCC_L007_R2_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_22GM2CLT3_AAGGATGT_L008_R1_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_22GM2CLT3_AAGGATGT_L008_R2_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_22GM3CLT3_AAGGATGT_L001_R1_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_22GM3CLT3_AAGGATGT_L001_R2_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_WGWGS_L86820_22GM3CLT3_CCTATGCC_L002_R1_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_WGWGS_L86820_22GM3CLT3_CCTATGCC_L002_R2_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_223JFNLT4_AAGGATGT_L001_R1_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_223JFNLT4_AAGGATGT_L001_R2_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_WGWGS_L86820_223JFNLT4_CCTATGCC_L002_R1_001.fastq.gz  
AIPECGS_49601_2_PB_Whole_C1_WGWGS_L86820_223JFNLT4_CCTATGCC_L002_R2_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_223JFYLT4_AAGGATGT_L005_R1_001.fastq.gz  
AIPECGS_49601_1_KI_Whole_T1_WGWGS_L86821_223JFYLT4_AAGGATGT_L005_R2_001.fastq.gz  

We have quite a few fastqs here to work with and multiple sequencing flowcells and lanes of data. The command line here will be complex, but not much more complex than our first two cases, demonstrating the power of pattern matching. The command line to be used here is:

```console
python3 fastq_to_json.py \
-n AIPECGS_49601 \ # Name of the submission and json
-i /path/to/input/data \ # Input path/prefix to where the fastqs are stored
-ap WGWGS="*WGWGS*",K1ID2="*K1ID2*",K1RIB="*K1RIB*" \ # Assigning assayCode
-gpp Genome="*WGWGS*",Capture="*K1ID2*",RNA="*K1RIB*" \ # Assigning glprep
-gtp Genome="*WGWGS*",Exome="*K1ID2*",RNA="*K1RIB*" \ # Assigning gltype
-sgp "Constitutional=*_C1_*,Tumor=*_T1_*" \ # Assigning subgroup . . .
-smf 1-7 \ # Yields AIPECGS_49601_2_PB_Whole_C1_K1ID2
-snf 1-8 \ # Yields AIPECGS_49601_2_PB_Whole_C1_K1ID2_L85409
-lbf 8 \ # Yields h092334-01D-01L
-p tempe@v1.2.1 \ # Pipeline and version to submit to
-s AIPECGS \ # Study name
-t template.json # Path to a template json to use for defining tasks
```
