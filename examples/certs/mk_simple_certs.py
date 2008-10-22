"""
Create certificates and private keys for the 'simple' example.
"""

from OpenSSL import crypto
from certgen import *   # yes yes, I know, I'm lazy

cakey = createKeyPair(TYPE_RSA, 2048)
careq = createCertRequest(cakey, CN='Server Certificate Authority')
cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*5)) # five years
open('serverca.key', 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey))
open('serverca.pem', 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert))
for (fname, cname) in [('server', 'Server')]:
    pkey = createKeyPair(TYPE_RSA, 2048)
    req = createCertRequest(pkey, CN=cname)
    cert = createCertificate(req, (cacert, cakey), 1, (0, 60*60*24*365*5)) # five years
    open('%s.key' % (fname,), 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
    open('%s.pem' % (fname,), 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

cakey = createKeyPair(TYPE_RSA, 2048)
careq = createCertRequest(cakey, CN='Client Certificate Authority')
cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*5)) # five years
open('clientca.key', 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey))
open('clientca.pem', 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert))
