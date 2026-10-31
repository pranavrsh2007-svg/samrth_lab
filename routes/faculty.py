import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from models import Complaint, Computer, User, MaintenanceRecord
from services.auth_service import login_required, role_required, get_current_user

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@faculty_bp.route('/dashboard')
@login_required
@role_required('faculty')
def dashboard():
    user = get_current_user()
    complaints = Complaint.get_by_faculty(user.id)
    
    total = len(complaints)
    pending = sum(1 for c in complaints if c.status == 'Pending')
    in_progress = sum(1 for c in complaints if c.status in ('Accepted', 'In Progress'))
    resolved = sum(1 for c in complaints if c.status in ('Resolved', 'Closed'))
    open_count = pending + in_progress

    recent_complaints = complaints[:5]

    return render_template('faculty/dashboard.html',
                           user=user,
                           total_complaints=total,
                           open_complaints=open_count,
                           pending_complaints=pending,
                           in_progress_complaints=in_progress,
                           resolved_complaints=resolved,
                           recent_complaints=recent_complaints)


@faculty_bp.route('/report-fault', methods=['GET', 'POST'])
@login_required
@role_required('faculty')
def report_fault():
    user = get_current_user()

    if request.method == 'POST':
        computer_id = request.form.get('computer_id', type=int)
        problem_category = request.form.get('problem_category', '').strip()
        priority = request.form.get('priority', '').strip()
        description = request.form.get('description', '').strip()

        # Validation
        if not computer_id or not problem_category or not priority or not description:
            flash('All required fields (Location, Computer, Category, Priority, and Description) must be provided.', 'danger')
            return redirect(url_for('faculty.report_fault'))

        if problem_category not in Complaint.CATEGORIES:
            flash('Invalid problem category selected.', 'danger')
            return redirect(url_for('faculty.report_fault'))

        if priority not in [Complaint.PRIORITY_LOW, Complaint.PRIORITY_MEDIUM, Complaint.PRIORITY_HIGH, Complaint.PRIORITY_CRITICAL]:
            flash('Invalid priority level selected.', 'danger')
            return redirect(url_for('faculty.report_fault'))

        computer = Computer.find_by_id(computer_id)
        if not computer:
            flash('Selected computer workstation does not exist in inventory.', 'danger')
            return redirect(url_for('faculty.report_fault'))

        if computer.operational_status == 'Decommissioned' or not computer.is_active:
            flash('This computer has been decommissioned and cannot accept new fault reports.', 'danger')
            return redirect(url_for('faculty.report_fault'))

        # Handle attachment
        attachment_filename = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    from services.storage_service import save_uploaded_file
                    saved_ref = save_uploaded_file(file)
                    if saved_ref:
                        attachment_filename = saved_ref
                    else:
                        flash('Failed to save attachment. Continuing with report submission.', 'warning')
                else:
                    flash('Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP, GIF.', 'warning')

        # Create Complaint record
        new_complaint = Complaint.create(
            faculty_id=user.id,
            computer_id=computer_id,
            problem_category=problem_category,
            priority=priority,
            description=description,
            attachment_filename=attachment_filename
        )

        return render_template('faculty/report_success.html',
                               complaint=new_complaint,
                               computer=computer)

    # Categories and priorities for form
    return render_template('faculty/report_fault.html',
                           user=user,
                           categories=Complaint.CATEGORIES,
                           priorities=[Complaint.PRIORITY_LOW, Complaint.PRIORITY_MEDIUM, Complaint.PRIORITY_HIGH, Complaint.PRIORITY_CRITICAL])


@faculty_bp.route('/my-complaints')
@login_required
@role_required('faculty')
def my_complaints():
    user = get_current_user()
    complaints = Complaint.get_by_faculty(user.id)
    return render_template('faculty/my_complaints.html',
                           user=user,
                           complaints=complaints)


@faculty_bp.route('/complaint/<string:code>')
@login_required
@role_required('faculty')
def complaint_detail(code):
    user = get_current_user()
    complaint = Complaint.find_by_code(code)
    if not complaint or complaint.faculty_id != user.id:
        flash('Complaint not found or access unauthorized.', 'danger')
        return redirect(url_for('faculty.my_complaints'))

    maintenance = MaintenanceRecord.get_by_complaint_id(complaint.id)
    computer = Computer.find_by_id(complaint.computer_id)

    return render_template('faculty/complaint_detail.html',
                           user=user,
                           complaint=complaint,
                           computer=computer,
                           maintenance=maintenance)
