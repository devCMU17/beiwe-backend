
from flask import Blueprint, request, abort, json, render_template

from kitchen.text.converters import to_bytes as thingy

from data.constants import (ALLOWED_EXTENSIONS, ANSWERS_TAG, TIMINGS_TAG,
                            DAILY_SURVEY_NAME, WEEKLY_SURVEY_NAME)
from libs.data_handlers import get_survey_results
from libs.db_models import User
from libs.s3 import s3_retrieve, s3_list_files, s3_upload, get_client_public_key_string
from libs.user_authentication import authenticate_user, authenticate_user_registration
from pages.survey_designer import get_latest_survey


################################################################################
############################# GLOBALS... #######################################
################################################################################
mobile_api = Blueprint('mobile_api', __name__)

################################################################################
############################# DOWNLOADS ########################################
################################################################################

# TODO: Josh/Eli, this function appears unused in the android app,
#  but I'm not positive.  remove it if no problems occur when it is commented out
#  (note: s3 retrieve is used here, otherwise unused)
# @mobile_api.route('/fetch_survey', methods=['GET', 'POST'])
# @authenticate_user
# def fetch_survey():
#     """ Method responsible for serving the latest survey JSON. """
#     return s3_retrieve("all_surveys/current_survey")


# TODO: josh. check that this to works with user authentication
@mobile_api.route('/download_daily_survey', methods=['GET', 'POST'])
@authenticate_user
def download_daily_survey():
    return get_latest_survey('daily')

@mobile_api.route('/download_weekly_survey', methods=['GET', 'POST'])
#@authenticate_user
def download_weekly_survey():
    return get_latest_survey('weekly')

################################################################################
############################# graph data #######################################
################################################################################


@mobile_api.route('/graph', methods=['GET', 'POST'])
#@authenticate_user
def fetch_graph():
    """ Fetches the patient's answers to the most recent survey, marked by
        survey ID. The results are dumped into a jinja template and pushed
        to the device."""
    patient_id = request.values['patient_id']
    data_results = []
    
    #results is a list of lists
    # inner list 0 is the title/question text
    # inner list 1 is a list of y coordinates
    results = get_survey_results(username=patient_id, survey_type=DAILY_SURVEY_NAME)
    for pair in results:
        
        coordinates = [json.dumps(coordinate) for coordinate in pair[1] ]
        # javascript understands json null/none values but not python Nones,
        # we must dump all variables individually.
        data_results.append( [ json.dumps( pair[0] ), coordinates ] )
        
    return render_template("phone_graphs.html", graphs=data_results)


################################################################################
################################ UPLOADS #######################################
################################################################################

@mobile_api.route('/upload', methods=['POST'])
@authenticate_user
def upload():
    """ Entry point to relay GPS, Accelerometer, Audio, PowerState, Calls Log,
        Texts Log, and Survey Response files. """
    patient_id = request.values['patient_id']
    uploaded_file = request.values['file']
    file_name = request.values['file_name']

    print "file name:", file_name
    #print "uploaded file = ", uploaded_file

    if uploaded_file and file_name and allowed_extension( file_name ):
        file_type, timestamp  = parse_filename( file_name )
        
        if ANSWERS_TAG in file_type or TIMINGS_TAG in file_type:
            ftype, parsed_id = parse_filetype( file_type )

            survey_type = 'UNKNOWN_TYPE'
            if 'daily' in ftype.lower(): survey_type = DAILY_SURVEY_NAME
            if 'weekly' in ftype.lower(): survey_type = WEEKLY_SURVEY_NAME
            if ftype.startswith( ANSWERS_TAG ): ftype = ANSWERS_TAG
            if ftype.startswith( TIMINGS_TAG ): ftype = TIMINGS_TAG
            
            s3_filename = (patient_id + '/' + ftype + '/' + survey_type + '/' +
                           parsed_id + '/' + timestamp)
            s3_upload(s3_filename, uploaded_file)
            
        else:
            if file_name[-4:] == ".mp4":
                print len(uploaded_file)
            s3_upload( file_name.replace("_", "/") , uploaded_file )
        return render_template('blank.html'), 200
    else:
        print "an upload failed."
        # Did not match any data upload files
        return abort(400)


@mobile_api.route('/register_user', methods=['GET', 'POST'])
@authenticate_user_registration
def register_user():
    """ Checks that the patient id has been granted, and that there is no device
        registered with that id.  If the patient id has no device registered it
        registers this device and logs the bluetooth mac address.
        Returns the encryption key for this patient. """
    #Case: If the id and password combination do not match, the decorator returns
    # a 403 error.
    patient_id = request.values['patient_id']
    mac_address = request.values['bluetooth_id']
    user = User(patient_id)
    if user['device_id'] is not None and user['device_id'] != request.values['device_id']:
        # Case: this patient has a different registered a device.  HTTP 405 is
        # the "method not allowed" error, seems like a good response to me.
        return abort(405)
    upload_bluetooth(patient_id, mac_address)
    print "device id:", request.values['device_id']
    user.set_device( request.values['device_id'] )
    #Case: this device has been registered successfully, the return is the
    # encryption key associated with this user.
    return get_client_public_key_string(patient_id), 200


################################################################################
############################### USER FUNCTIONS #################################
################################################################################

@mobile_api.route('/set_password', methods=['GET', 'POST'])
@authenticate_user
def set_password():
    """ After authenticating a user, sets the new password and returns 200."""
    User(request.values["patient_id"]).set_password(request.values["new_password"])
    return render_template('blank.html'), 200


################################################################################
############################ RELATED FUNCTIONALITY #############################
################################################################################

def upload_bluetooth( patient_id, mac_address ):
    """ Uploads the user's bluetooth mac address safely. """
    number_mac_addresses = len( s3_list_files(patient_id + '/mac' ) )
    s3_upload(patient_id + '/mac_' + str(number_mac_addresses),
                             mac_address )

def parse_filename(filename):
    """ Splits filename into user-id, file-type, unix-timestamp. """
    name = filename.split("_")
    if len(name) == 3:
        return name[1], name[2]

def parse_filetype(file_type):
    """ Separates alphabetical characters from digits for parsing."""
    parsed_id = filter(str.isdigit, str(file_type))
    return filter(str.isalpha, str(file_type)), parsed_id

def allowed_extension(filename):
    """ Checks if string has a recognized file extension. """
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
