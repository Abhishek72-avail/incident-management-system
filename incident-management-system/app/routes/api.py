# app/routes/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.incident import Incident
from app.models.user import User
from app.models.comment import Comment
from app.database import db
from datetime import datetime
from app.email_service import send_incident_notification, send_assignment_notification, send_status_update_notification
from functools import wraps

api_bp = Blueprint('api', __name__)

# Custom decorator for API authentication
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# API route to get all incidents
@api_bp.route('/incidents', methods=['GET'])
@api_login_required
def get_incidents():
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
    
    return jsonify({
        'incidents': [incident.to_dict() for incident in incidents]
    })

# API route to get a specific incident
@api_bp.route('/incidents/<int:incident_id>', methods=['GET'])
@api_login_required
def get_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    return jsonify(incident.to_dict())

# API route to create an incident
@api_bp.route('/incidents', methods=['POST'])
@api_login_required
def create_incident():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['title', 'description', 'incident_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    incident = Incident(
        title=data['title'],
        description=data['description'],
        priority=data.get('priority', 'medium'),
        incident_type=data['incident_type'],
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
    
    return jsonify({
        'message': 'Incident created successfully',
        'incident': incident.to_dict()
    }), 201

# API route to update an incident
@api_bp.route('/incidents/<int:incident_id>', methods=['PUT'])
@api_login_required
def update_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    # Check if user has permission to update
    if current_user.id != incident.creator_id and current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'You do not have permission to update this incident'}), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'title' in data:
        incident.title = data['title']
    
    if 'description' in data:
        incident.description = data['description']
    
    if 'priority' in data:
        incident.priority = data['priority']
    
    if 'incident_type' in data:
        incident.incident_type = data['incident_type']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Incident updated successfully',
        'incident': incident.to_dict()
    })

# API route to assign an incident
@api_bp.route('/incidents/<int:incident_id>/assign', methods=['POST'])
@api_login_required
def assign_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    # Check if user has permission to assign
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'You do not have permission to assign this incident'}), 403
    
    data = request.get_json()
    
    if not data or 'assignee_id' not in data:
        return jsonify({'error': 'No assignee_id provided'}), 400
    
    assignee = User.query.get(data['assignee_id'])
    
    if not assignee:
        return jsonify({'error': 'Invalid assignee_id'}), 400
    
    incident.assignee_id = assignee.id
    incident.status = 'in_progress'
    db.session.commit()
    
    # Send email notification to assignee
    send_assignment_notification(incident, [assignee.email])
    
    return jsonify({
        'message': 'Incident assigned successfully',
        'incident': incident.to_dict()
    })

# API route to update incident status
@api_bp.route('/incidents/<int:incident_id>/status', methods=['POST'])
@api_login_required
def update_status(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    # Check if user has permission to update status
    if current_user.id != incident.assignee_id and current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'You do not have permission to update the status of this incident'}), 403
    
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'No status provided'}), 400
    
    status = data['status']
    
    if status not in ['open', 'in_progress', 'resolved', 'closed']:
        return jsonify({'error': 'Invalid status value'}), 400
    
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
    
    return jsonify({
        'message': f'Status updated to {status} successfully',
        'incident': incident.to_dict()
    })

# API route to add a comment
@api_bp.route('/incidents/<int:incident_id>/comments', methods=['POST'])
@api_login_required
def add_comment(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'No comment content provided'}), 400
    
    comment = Comment(
        content=data['content'],
        incident_id=incident_id,
        author_id=current_user.id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'message': 'Comment added successfully',
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author_id': comment.author_id,
            'author_name': User.query.get(comment.author_id).username,
            'created_at': comment.created_at.isoformat()
        }
    }), 201

# API route to get comments for an incident
@api_bp.route('/incidents/<int:incident_id>/comments', methods=['GET'])
@api_login_required
def get_comments(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    comments = Comment.query.filter_by(incident_id=incident_id).order_by(Comment.created_at).all()
    
    return jsonify({
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'author_id': comment.author_id,
            'author_name': User.query.get(comment.author_id).username,
            'created_at': comment.created_at.isoformat()
        } for comment in comments]
    })