import os
import re
import sys
import json
import glob
import gzip
import random
import fnmatch
import argparse
import subprocess
from difflib import SequenceMatcher

currentDirectory = os.getcwd()
hpcAccount = subprocess.check_output("sacctmgr list user where user=$USER -o format=user%20,DefaultAccount%20 | tail -n1 | awk '{ print $2 }'", shell=True).decode('utf-8').rstrip()
centro_url = "http://jetstream-centro.ad.tgen.org:9000/api/v1/new-run/"

def parse_arguments():
    """Parse arguments, validate and return the args"""

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-n', '--name', default="EXAMPLE", help='Name of the json to generate, also becomes the name of the project when submitted')
    parser.add_argument('-i', '--input', nargs='+', default=currentDirectory, help='Input directory and prefix of fastqs to process, ', metavar='/path/to/input_fastqs')
    parser.add_argument('-rp', '--readPattern', default='*R1*.fastq.gz', help='Glob pattern for R1 fastqs, R2 will simply replace R1 with R2 in this pattern, default = *R1*.fastq.gz', metavar='readPattern')
    parser.add_argument('-o', '--output', default=currentDirectory, help='Output directory to place the name.json', metavar='/path/to/output/directory')
    parser.add_argument('-t', '--template', help='Path to a template json to copy task configuration from', metavar='/path/to/template.json')
    parser.add_argument('-s', '--study', default="STUDY", help='Name of the study, e.g. MMRF, C4RCD, TCL, etc', metavar='STUDY')
    parser.add_argument('-c', '--center', help='Center the data originates from, defaults to TGen', metavar='Center')
    parser.add_argument('-m', '--model', help='Platform model the data is from, defaults to NovaSeq6000', metavar='PlatformModel')
    parser.add_argument('-a', '--assay', help='If defined, this assayCode will be used for all data_files', metavar='ASSAY')
    parser.add_argument('-ap', '--assayPattern', help='Glob pattern to use for assigning an assayCode, assignment is split on "=", example: K1ID2="*_ID2_*",KHWGS="*_WGS_*"', metavar='assayPattern')
    parser.add_argument('-af', '--assayField', help='Assuming the fastq naming scheme is uniform, what field(s) should be used for assigning assayCode.\n'
                        'For example to extract ASSAY from STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY.fastq.gz we would use: 7', metavar='assayField')
    parser.add_argument('-gp', '--glprep', help='If defined, glPrep of all data_files, Genome, Capture, or RNA in most cases', metavar='glPrep')
    parser.add_argument('-gpp', '--glprepPattern', help='Glob pattern to use for assigning glPrep, assignment is split on "="\n'
                        'For example: Genome="*WGS*",Capture="*WES*"', metavar='glprepPattern')
    parser.add_argument('-gt', '--gltype', help='If defined, glType of all data_files, Genome, Exome, or RNA in most cases', metavar='glType')
    parser.add_argument('-gtp', '--gltypePattern', help='Glob pattern to use for assigning glType, assignment is split on "="\n'
                        'For example: Genome="*WGS*",Exome="*WES*"', metavar='gltypePattern')
    parser.add_argument('-sg', '--subgroup', help='Sample type, tumor or constitutional', metavar='subGroup')
    parser.add_argument('-sgp', '--subgroupPattern', help='Glob pattern to use for assigning subGroup, assignment is split on "="\n'
                        'For example: Tumor="*_T1_*"', metavar='subgroupPattern')
    parser.add_argument('-drmk', '--dnaRnaMergeKey', help='If defined, dnaRnaMergeKey of all data_files', metavar='dnaRnaMergeKey')
    parser.add_argument('-drmkf', '--dnaRnaMergeKeyField', help='Assuming the fastq naming scheme is uniform, what field(s) should be used for assigning dnaRnaMergeKey.\n'
                        'For example to extract STUDY_PATIENT_VISIT_SOURCE_FRACTION from STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY.fastq.gz we would use: 1,2,3,4,5 or 1-5', metavar='dnaRnaMergeKeyField')
    parser.add_argument('-smk', '--sampleMergeKey', help='If defined, sampleMergeKey of all data_files', metavar='sampleMergeKey')
    parser.add_argument('-smkf', '--sampleMergeKeyField', help='Assuming the fastq naming scheme is uniform, what field(s) should be used for assigning sampleMergeKey.\n'
                        'For example to extract STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY from STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY.fastq.gz we would use: 1,2,3,4,5,6,7 or 1-7', metavar='sampleMergeKeyField')
    parser.add_argument('-sn', '--sampleName', help='If defined, sampleName of all data_files', metavar='sampleName')
    parser.add_argument('-snf', '--sampleNameField', help='Assuming the fastq naming scheme is uniform, what field(s) should be used for assigning sampleName.\n'
                        'For example to extract STUDY_PATIENT from STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY.fastq.gz we would use: 1,2 or 1-2', metavar='sampleNameField')
    parser.add_argument('-sm', '--rgsm', help='If defined, rgsm of all data_files', metavar='rgsm')
    parser.add_argument('-smf', '--rgsmField', help='Assuming the fastq naming scheme is uniform, what field(s) should be used for assigning rgsm.\n'
                        'For example to extract STUDY_PATIENT_VISIT_SOURCE_FRACTION from STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY.fastq.gz we would use: 1,2,3,4,5 or 1-5', metavar='rgsmField')
    parser.add_argument('-lb', '--rglb', help='If defined, rglb of all data_files', metavar='rglb')
    parser.add_argument('-lbf', '--rglbField', help='Assuming the fastq naming scheme is uniform, what field(s) should be used for assigning rglb.\n'
                        'For example to extract LIBRARY from STUDY_PATIENT_VISIT_SOURCE_FRACTION_SubgroupIncrement_ASSAY_LIBRARY.fastq.gz we would use: 8', metavar='rglbField')
    parser.add_argument('-P', '--isilonPath', default=f"/scratch/{os.environ.get('USER')}/", help='Path to the results archive', metavar='/path/to/project/results')
    parser.add_argument('-p', '--pipeline', default="tempe@latest", help='Name of the pipeline you would like to run', metavar='pipeline@version')
    parser.add_argument('-A', '--account', default=hpcAccount, help=f'Slurm account to bill to, defaults to the default account found in sacctmgr, {hpcAccount}.', metavar='hpcAccount')
    parser.add_argument('-C', '--cram', default=False, action='store_true', help='Set the pipeline alignment output to cram instead of bam')
    parser.add_argument('-S', '--sex', default="Unknown", help='Sex of the sample, Male or Female, default is Unknown')
    parser.add_argument('-d', '--dummy', default=False, action='store_true', help='Use dummy values for most fields')
    parser.add_argument('-e', '--email', default=f"{os.environ.get('USER')}@tgen.org", help='Your email; can also be a comma separated list')
    parser.add_argument('-nc', '--noCompute', default=False, action='store_true', help='Skip calculation heavy extractions from the fastq')
    parser.add_argument('--resplit', default='_|-', help='Modifies the re used for splitting the fastq name into separate fields. By default we split on "_" and "-".', metavar='\'_|-\'')
    parser.add_argument('--submit', default=False, action='store_true', help='Submit the generated json to jetstream centro')
    parser.add_argument('--centro', default=centro_url, help=f'URL to submit the json to if --submit is enabled, defaults to {centro_url}', metavar='centro_url')
    parser.add_argument('--netrc', help='Path a netrc formatted file for authentication with the centro server', metavar='/path/to/netrc')
    parser.add_argument('--dryRun', default=False, action='store_true', help='Mock the submission to centro, but generate the complete json.')

    # prints help message when 0 arguments are entered
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    parser_args = parser.parse_args()

    return parser_args


def longestCommonSubstring(strs):
    longest_common_substring = ""
    for i in range(1, len(strs)):
        if i == 1:
            string1, string2 = strs[0], strs[i]
        else:
            string1, string2 = longest_common_substring, strs[i]
        match = SequenceMatcher(None, string1, string2).find_longest_match(0, len(string1), 0, len(string2))
        longest_common_substring = string1[match.a: match.a + match.size]
    return longest_common_substring.strip('_')


def longestCommonPrefix(strs):
    length = 0
    for i in range(1, len(strs)):
        length = min(len(strs[0]), len(strs[i]))
        while length > 0 and strs[0][0:length] != strs[i][0:length]:
            length = length - 1
            if length == 0:
                return 0
    return strs[0][0:length].rstrip('_')


def find_fastqs_in_dir(input, readPattern):
    fastq_list = []
    for dir in input:
        fastq_list += glob.glob(f'{dir}{readPattern}')
    if len(fastq_list) == 0:
        raise RuntimeError(f'No fastqs found in {input}')
    return fastq_list


def get_pattern_match(fastq, pattern, fallback, default):
    if pattern is not None:
        pattern = pattern.rstrip() + ','
        pattern_dict = dict(p.split("=")[::-1] for p in pattern.split(",") if p != '')
        for key, value in pattern_dict.items():
            if fnmatch.fnmatch(fastq, key):
                return value
    if fallback is not None:
        return fallback
    elif default is not None:
        return default
    else:
        return None


def get_selected_fields(fastq, fields, resplit):
    fields = fields + ','
    fields_list = []
    for i in filter(None, fields.split(",")):
        if "-" in i:
            s, e = i.split("-")
            fields_list.extend(range(int(s) - 1, int(e)))
        else:
            fields_list.append(int(i) - 1)
    extracted_fields = list(map(re.split(resplit, fastq).__getitem__, fields_list))
    return '_'.join(extracted_fields)


def get_line_count(fastq):
    def _make_gen(reader):
        while True:
            b = reader(2 ** 16)
            if not b:
                break
            yield b

    with gzip.open(fastq, "rb") as f:
        count = sum(buf.count(b"\n") for buf in _make_gen(f.read))
    return count


def create_data_files_from_fastqs(fastq_list, args):
    data_files = []
    if len(fastq_list) > 1:
        sampleName = longestCommonPrefix(list(map(os.path.basename, fastq_list)))
    else:
        sampleName = args.name
    for fastq in fastq_list:
        print(f'parsing fastq: {fastq}')
        fastq_dict = {}
        count = 0
        with gzip.open(fastq, 'rb') as f:
            first_line = f.readline().decode().rstrip('\n')
        if not args.noCompute:
            print(f'counting number of lines in {fastq} ..... to skip this process, press CTRL+C to interrupt and run the script with the -nc/--noCompute option')
            count = get_line_count(fastq)

        random.seed(first_line, version=2)
        random_bc = ''.join(random.choices(['A', 'T', 'G', 'C'], k=8))

        fastq_dict['assayCode'] = get_selected_fields(os.path.basename(fastq), args.assayField, args.resplit) if args.assayField else get_pattern_match(fastq, args.assayPattern, args.assay, 'KHWGS')
        fastq_dict['fastqCode'] = 'R1'
        fastq_dict['fastqPath'] = fastq
        fastq_dict['fileType'] = 'fastq'
        fastq_dict['glPrep'] = get_pattern_match(fastq, args.glprepPattern, args.glprep, 'Genome')
        fastq_dict['glType'] = get_pattern_match(fastq, args.gltypePattern, args.gltype, 'Genome')
        fastq_dict['flowcell'] = "FLOWCELL" if args.dummy else first_line.split(':')[2]
        fastq_dict['lane'] = "1" if args.dummy else first_line.split(':')[3]
        if not args.noCompute:
            fastq_dict['numberOfReads'] = int(count / 2)
        fastq_dict['read1Length'] = int(subprocess.check_output(f"zcat {fastq} | head -n 1000 | wc -L", shell=True).decode('utf-8').rstrip())
        fastq_dict['read2Length'] = fastq_dict['read1Length']
        fastq_dict['rgcn'] = args.center if args.center else 'TGen'
        fastq_dict['rgpl'] = 'ILLUMINA'
        fastq_dict['rgpm'] = args.model if args.model else 'NovaSeq6000'
        fastq_dict['rgbc'] = random_bc if args.dummy else first_line.split(':')[9].replace('+', '-')
        fastq_dict['rgpu'] = f"{fastq_dict['flowcell']}_{fastq_dict['lane']}"
        fastq_dict['rgid'] = f"{fastq_dict['rgpu']}_{fastq_dict['rgbc']}"
        fastq_dict['rgsm'] = get_selected_fields(os.path.basename(fastq), args.rgsmField, args.resplit) if args.rgsmField else args.rgsm if args.rgsm else sampleName
        fastq_dict['rglb'] = get_selected_fields(os.path.basename(fastq), args.rglbField, args.resplit) if args.rglbField else args.rglb if args.rglb else sampleName
        if args.dnaRnaMergeKey or args.dnaRnaMergeKeyField:
            fastq_dict['dnaRnaMergeKey'] = get_selected_fields(os.path.basename(fastq), args.dnaRnaMergeKeyField, args.resplit) if args.dnaRnaMergeKeyField else args.dnaRnaMergeKey
        if args.sampleMergeKey or args.sampleMergeKeyField:
            fastq_dict['sampleMergeKey'] = get_selected_fields(os.path.basename(fastq), args.sampleMergeKeyField, args.resplit) if args.sampleMergeKeyField else args.sampleMergeKey
        fastq_dict['sampleName'] = get_selected_fields(os.path.basename(fastq), args.sampleNameField, args.resplit) if args.sampleNameField else args.sampleName if args.sampleName else sampleName
        fastq_dict['subGroup'] = get_pattern_match(fastq, args.subgroupPattern, args.subgroup, 'Constitutional')
        data_files.append(fastq_dict)
        # Duplicate the entry for R2
        fastq_dict_r2 = fastq_dict.copy()
        fastq_dict_r2['fastqCode'] = 'R2'
        # We only want to replace the last R1 with R2, otherwise we would use a simple str.replace()
        fastq_dict_r2['fastqPath'] = 'R2'.join(fastq.rsplit('R1', 1))
        data_files.append(fastq_dict_r2)

    return data_files


def main():
    # Parse and validate arguments
    args = parse_arguments()

    fastq_list = find_fastqs_in_dir(args.input, args.readPattern)
    output_json = f"{args.output}/{args.name}.json"
    data_files = create_data_files_from_fastqs(fastq_list, args)

    template = None
    if args.template:
        if os.path.exists(args.template):
            with open(args.template, 'r') as f:
                template = json.load(f)
        else:
            print(f'{args.template} does not appear to exist, using empty task list')

    # Creating fields/objects for json output
    output_dict = {"dataFiles": []}
    output_dict['cram'] = True if args.cram else False
    output_dict['dataFiles'] = data_files
    output_dict['email'] = args.email
    output_dict['ethnicity'] = "Unknown"
    output_dict['hpcAccount'] = args.account
    output_dict['isilonPath'] = args.isilonPath
    output_dict['pipeline'] = args.pipeline
    output_dict['project'] = args.name
    output_dict['sex'] = args.sex
    output_dict['study'] = args.study
    output_dict['studyDisease'] = ""
    output_dict['tasks'] = template['tasks'] if template is not None else ""

    with open(output_json, 'w') as output_file:
        json.dump(output_dict, output_file, indent=2)

    if args.submit:
        if args.dryRun:
            print('Dry Run enabled, command to submit json is:')
            print(f'curl --request POST --netrc-file {args.netrc} --header "Content-type: application/json" -d @{output_json} {args.centro}')
        else:
            submission = subprocess.run(f'curl --request POST --netrc-file {args.netrc} --header "Content-type: application/json" -d @{output_json} {args.centro}', shell=True, capture_output=True)
            if submission.returncode == 0:
                print(f'Success! {output_json} has been submitted to {args.centro}')
            else:
                print(f'Error! {output_json} was rejected by {args.centro}, or could not be reached')


if __name__ == '__main__':
    main()
