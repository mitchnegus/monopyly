"""
Routes for financial analytics.
"""

from dry_foundation.database import db_transaction
from flask import g, render_template, request

from ..auth.tools import login_required
from ..common.transactions import TransactionTagHandler
from .actions import get_tag_statistics_chart_data
from .blueprint import bp


@bp.route("/tags")
@login_required
def load_tags():
    # Get the tag hierarchy from the database
    hierarchy = TransactionTagHandler.get_hierarchy()
    return render_template("common/tags_page.html", tags_hierarchy=hierarchy)


@bp.route("/_add_tag", methods=("POST",))
@login_required
@db_transaction
def add_tag():
    # Get the new tag (and potentially parent category) from the AJAX request
    post_args = request.get_json()
    tag_name = post_args["tag_name"]
    parent_name = post_args.get("parent")
    # Check that the tag name does not already exist
    if TransactionTagHandler.get_tags(tag_names=(tag_name,)):
        raise ValueError("The given tag name already exists. Tag names must be unique.")
    parent_id = TransactionTagHandler.find_tag(parent_name).id if parent_name else None
    tag = TransactionTagHandler.add_entry(
        parent_id=parent_id,
        user_id=g.user.id,
        tag_name=tag_name,
    )
    return render_template("common/tag_tree.html", tags_hierarchy={tag: []})


@bp.route("/_delete_tag", methods=("POST",))
@login_required
@db_transaction
def delete_tag():
    # Get the tag to be deleted from the AJAX request
    post_args = request.get_json()
    tag_name = post_args["tag_name"]
    tag = TransactionTagHandler.find_tag(tag_name)
    # Remove the tag from the database
    TransactionTagHandler.delete_entry(tag.id)
    return ""


@bp.route("/tag_statistics")
@login_required
def show_tag_statistics():
    hierarchy = TransactionTagHandler.get_hierarchy()
    return render_template(
        "analytics/tag_statistics/tag_statistics_page.html",
        tags_hierarchy=hierarchy,
        chart_data=get_tag_statistics_chart_data(hierarchy.keys()),
    )


@bp.route("/_update_tag_statistics_chart", methods=("POST",))
@login_required
def update_tag_statistics_chart():
    # Get the field from the AJAX request
    tag_id = int(request.get_json())
    tags = (
        [TransactionTagHandler.get_entry(tag_id)]
        if tag_id
        else TransactionTagHandler.get_hierarchy()
    )
    return render_template(
        "analytics/tag_statistics/tag_statistics.html",
        chart_data=get_tag_statistics_chart_data(tags),
    )
