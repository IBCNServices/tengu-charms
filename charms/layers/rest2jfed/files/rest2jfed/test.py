import json
import jfed_utils
import re

output="""Using speaksFor credential for user "urn:publicid:IDN+wall2.ilabt.iminds.be+user+mesebrec"
slice urn:publicid:IDN+wall2.ilabt.iminds.be:tengu+slice+klsdlds does not yet exist
Contacting  urn:publicid:IDN+wall1.ilabt.iminds.be+authority+cm...
Error creating sliver at urn:publicid:IDN+wall1.ilabt.iminds.be+authority+cm: "{
"output": "Could not allocate public address pools",
"code": {
             "protogeni_error_url": "https://www.wall1.ilabt.iminds.be/spewlogfile.php3?logfile=15a383a4e3b995a837f64a9f3b58add8",
             "protogeni_error_log": "urn:publicid:IDN+wall1.ilabt.iminds.be+log+15a383a4e3b995a837f64a9f3b58add8",
             "geni_code": 2,
             "am_type": "protogeni",
             "am_code": 2
             },
"value": 0
}"

"""
#regexstr = r'"{.*}"'
#print(re.search(regexstr, output, flags=re.DOTALL))

jfed_utils.parse_output(output, False)
