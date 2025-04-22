# app/routes/incidents.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.incident import Incident
from app.models.user import User
from app.models.comment import Comment
from app.database import db
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime
from app.email_service import send_incident_notification, send_assignment_notification, send_status_update_notification

incidents_bp = Blueprint('incidents', __name__)

class IncidentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), 
        ('medium', 'Medium'), 
        ('high', 'High'), 
        ('critical', 'Critical')
    ], default='medium')
    incident_type = SelectField('Type', choices=[
        ('infrastructure', 'Infrastructure'),
        ('application', 'Application'),
        ('security', 'Security'),
        ('network', 'Network'),
        ('database', 'Database'),
        ('other', 'Other')
    ])
    submit = SubmitField('Submit')

class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Add Comment')

@incidents_bp.route('/dashboard')
@login_required
def dashboard():
    # Get open incidents for the dashboard
    open_incidents = Incident.query.filter(Incident.status != 'closed').order_by(Incident.created_at.desc()).all()
    
    # Get statistics
    total_incidents = Incident.query.count()
    open_count = Incident.query.filter_by(status='open').count()
    in_progress_count = Incident.query.filter_by(status='in_progress').count()
    resolved_count = Incident.query.filter_by(status='resolved').count()
    closed_count = Incident.query.filter_by(status='closed').count()
    
    # Get incidents assigned to current user
    my_incidents = Incident.query.filter_by(assignee_id=current_user.id).filter(Incident.status != 'closed').all()
    
    # Get recent incidents created by current user
    created_incidents = Incident.query.filter_by(creator_id=current_user.id).order_by(Incident.created_at.desc()).limit(5).all()
    
    return render_template('incidents/dashboard.html', 
                          title='Dashboard',
                          open_incidents=open_incidents,
                          my_incidents=my_incidents,
                          created_incidents=created_incidents,
                          total_incidents=total_incidents,
                          open_count=open_count,
                          in_progress_count=in_progress_count,
                          resolved_count=resolved_count,
                          closed_count=closed_count)

@incidents_bp.route('/incidents')
@login_required
def list_incidents():
    # Filter incidents based on query parameters
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    type = request.args.get('type', '')
    
    query = Incident.query
    
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if type:
        query = query.filter_by(incident_type=type)
    
    incidents = query.order_by(Incident.created_at.desc()).all()
    
    return render_template('incidents/list.html', 
                          title='All Incidents', 
                          incidents=incidents,
                          status_filter=status,
                          priority_filter=priority,
                          type_filter=type)

@incidents_bp.route('/incidents/create', methods=['GET', 'POST'])
@login_required
def create_incident():
    form = IncidentForm()
    
    if form.validate_on_submit():
        incident = Incident(
            title=form.title.data,
            description=form.description.data,
            priority=form.priority.data,
            incident_type=form.incident_type.data,
            creator_id=current_user.id,
            status='open'
        )
        
        db.session.add(incident)
        db.session.commit()
        
        # Send email notification to admins and managers
        admin_emails = [user.email for user in User.query.filter_by(role='admin').all()]
        manager_emails = [user.email for user in User.query.filter_by(role='manager').all()]
        recipients = admin_emails + manager_emails
        
        if recipients:
            send_incident_notification(incident, recipients)
            # Continuing app/routes/incidents.py

        flash('Incident created successfully!')
        return redirect(url_for('incidents.view_incident', incident_id=incident.id))
    
    return render_template('incidents/create.html', title='Create Incident', form=form)

@incidents_bp.route('/incidents/<int:incident_id>')
@login_required
def view_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    comments = Comment.query.filter_by(incident_id=incident_id).order_by(Comment.created_at).all()
    comment_form = CommentForm()
    return render_template('incidents/view.html', 
                          title=incident.title, 
                          incident=incident, 
                          comments=comments, 
                          comment_form=comment_form)

@incidents_bp.route('/incidents/<int:incident_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    # Check if user has permission to edit
    if current_user.id != incident.creator_id and current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to edit this incident.')
        return redirect(url_for('incidents.view_incident', incident_id=incident.id))
    
    form = IncidentForm()
    
    if form.validate_on_submit():
        old_status = incident.status
        
        incident.title = form.title.data
        incident.description = form.description.data
        incident.priority = form.priority.data
        incident.incident_type = form.incident_type.data
        
        db.session.commit()
        
        flash('Incident updated successfully!')
        return redirect(url_for('incidents.view_incident', incident_id=incident.id))
    
    elif request.method == 'GET':
        form.title.data = incident.title
        form.description.data = incident.description
        form.priority.data = incident.priority
        form.incident_type.data = incident.incident_type
    
    return render_template('incidents/edit.html', title='Edit Incident', form=form, incident=incident)

@incidents_bp.route('/incidents/<int:incident_id>/comment', methods=['POST'])
@login_required
def add_comment(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            incident_id=incident_id,
            author_id=current_user.id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        flash('Comment added successfully!')
    
    return redirect(url_for('incidents.view_incident', incident_id=incident_id))

@incidents_bp.route('/incidents/<int:incident_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    # Check if user has permission to assign
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to assign this incident.')
        return redirect(url_for('incidents.view_incident', incident_id=incident.id))
    
    users = User.query.all()
    
    if request.method == 'POST':
        assignee_id = request.form.get('assignee_id')
        
        if assignee_id:
            incident.assignee_id = assignee_id
            incident.status = 'in_progress'
            db.session.commit()
            
            # Send email notification to assignee
            assignee = User.query.get(assignee_id)
            if assignee:
                send_assignment_notification(incident, [assignee.email])
            
            flash('Incident assigned successfully!')
            return redirect(url_for('incidents.view_incident', incident_id=incident.id))
    
    return render_template('incidents/assign.html', title='Assign Incident', incident=incident, users=users)

@incidents_bp.route('/incidents/<int:incident_id>/status', methods=['POST'])
@login_required
def update_status(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    # Check if user has permission to update status
    if current_user.id != incident.assignee_id and current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to update the status of this incident.')
        return redirect(url_for('incidents.view_incident', incident_id=incident.id))
    
    status = request.form.get('status')
    
    if status in ['open', 'in_progress', 'resolved', 'closed']:
        old_status = incident.status
        incident.status = status
        
        if status == 'resolved':
            incident.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send email notification to creator and stakeholders
        recipients = [User.query.get(incident.creator_id).email]
        if incident.assignee_id and incident.assignee_id != current_user.id:
            assignee = User.query.get(incident.assignee_id)
            recipients.append(assignee.email)
        
        if recipients:
            send_status_update_notification(incident, recipients)
        
        flash(f'Status updated to {status} successfully!')
    
    return redirect(url_for('incidents.view_incident', incident_id=incident.id))