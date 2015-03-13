def getusize(size):
    """
    return a user friendly size string
    """

    if size >= 1 << 40:
        return '%0.2f TB' % (size * 1.0 / (1 << 40))
    elif size >= 1 << 30:
        return '%0.2f GB' % (size * 1.0 / (1 << 30))
    elif size >= 1 << 20:
        return '%0.2f MB' % (size * 1.0 / (1 << 20))
    elif size >= 1 << 10:
        return '%0.2f KB' % (size * 1.0 / (1 << 10))
    else:
        return str(size) + ' B'

def send_email(email_content, email_to, email_from=None, email_subject=None):
    """
    Method to send an email to user.

    """

    import email
    from src import constants as C
    from smtplib import SMTP
    from smtplib import SMTPException

    if email_content is None:
        raise Exception('No email content supplied')
    if email_to is None:
        raise Exception('Email to address is missing')

    if email_subject is None:
        #Use the common email subject if not provided.
        email_subject = C.EMAIL_SUBJECT

    if email_from is None:
        email_from = C.EMAIL_FROM

    msg = email.message_from_string(email_content)
    msg['Subject'] = email_subject
    msg['From'] = email_from
    msg['To'] = email_to

    try:
      smtpObj = SMTP(C.GMAIL_SMTP, C.GMAIL_SMTP_PORT)
      #Identify yourself to GMAIL ESMTP server.
      smtpObj.ehlo()
      #Put SMTP connection in TLS mode and call ehlo again.
      smtpObj.starttls()
      smtpObj.ehlo()
      #Login to service
      smtpObj.login(user=C.GMAIL_USERNAME, password=C.GMAIL_PASSWORD)
      #Send email
      smtpObj.sendmail(C.EMAIL_FROM, C.EMAIL_TO, msg.as_string())
      #close connection and session.
      smtpObj.quit();
    except SMTPException as error:
      raise Exception('Error sending email')

def generate_random_password():
    """
    Generate random password for new user.
    It should satisfy following conidtions:
    1) min length: at least 8 characters.
    2) must have lower case letter.
    3) must have upper case letter.
    4) contain numbers.
    """
    import random
    import string
    LENGTH = 10
    pwd = ''.join(random.choice(string.ascii_uppercase + string.digits + \
                 string.ascii_lowercase) for _ in range(LENGTH))
    return pwd

def generate_encrypted_password(raw_password=None):
     """
     Generate secure password for new account created by admin.
     algorithm used: sha1

     """

     import random
     import hashlib

     rand1 = str(random.random()).encode('utf-8')
     rand2 = str(random.random()).encode('utf-8')
     salt  = hashlib.sha1(rand1 + rand2).hexdigest()[:10]
     hsh   = hashlib.sha1(salt.encode('utf-8') +  raw_password.encode('utf-8')).hexdigest()
     pwd   = '%s$%s' % (salt, hsh)
     return pwd

def generate_password(raw_password=None):
    """
    Method to generate user's password.

    """
    if raw_password is None:
        raw_password = generate_random_password()

    return generate_encrypted_password(raw_password)

def check_password(raw_password, encrypted_pwd):
    """
    Method to check whether password entered by user 
    is correct or not.

    """
    import random
    import hashlib
    salt, hsh = encrypted_pwd.split('$')
    hsh_raw = hashlib.sha1(salt.encode('utf-8') + raw_password.encode('utf-8')).hexdigest()
    return hsh == hsh_raw
