from flask import abort, Blueprint, render_template

from db.study_models import Studies, Survey
from libs.admin_authentication import authenticate_admin_study_access,\
    get_admins_allowed_studies, admin_is_system_admin

survey_designer = Blueprint('survey_designer', __name__)

#TODO: Low Priority. implement "study does not exist" page.
#TODO: Low Priority. implement "survey does not exist" page.

@survey_designer.route('/edit_survey/<string:survey_id>')
@authenticate_admin_study_access
def render_edit_survey(survey_id=None):
    survey = Survey(survey_id)
    study = [study for study in Studies() if survey['_id'] in study['surveys']][0]
    if not survey:
        return abort(404)
    return render_template('edit_survey.html', survey=survey, study=study,
                           allowed_studies=get_admins_allowed_studies(),
                           system_admin=admin_is_system_admin())