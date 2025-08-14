"""Views relating to both publication requests and the variation of their status, e.g. approval or rejection."""
from datetime import datetime
from django.db import transaction
from django.http import JsonResponse
from django.utils.timezone import make_aware
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateResponseMixin, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

import logging

from clinicalcode.entity_utils import constants, doi_utils, publish_utils, permission_utils
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity

logger = logging.getLogger(__name__)

class Publish(LoginRequiredMixin, permission_utils.HasAccessToViewGenericEntityCheckMixin, TemplateResponseMixin, View):
    """
    View to manage requests by user(s) to vary the status of a publication request.

    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms;
        - This has been temporarily documented & updated by @js/is in the meantime but this will require reimplementation.
    """
    model = GenericEntity
    template_name = 'clinicalcode/generic_entity/publish/publish.html'

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self, request, pk, history_id):
        """
        Handle GET requests by users initiating the publication process by opening the `js/entityPublish.js` modal

        Args:
            request (HttpRequest): the HTTP request context
            pk              (str): the ID of the entity
            history_id      (int): the version ID of the entity

        Returns:
            (JsonResponse): a JSON-encoded `HttpResponse` specifying entity & publication data required to initiate the publication process
        """
        checks = publish_utils.check_entity_to_publish(request, pk, history_id)
        checks['entity_id'] = pk
        checks['entity_history_id'] = history_id
        return JsonResponse(checks, safe=False)

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def post(self, request, pk, history_id):
        """
        Handle POST requests by users attempting to vary the publication status of an entity (approved/rejected/pending)

        Args:
            request (HttpRequest): the HTTP request context
            pk              (str): the ID of the entity
            history_id      (int): the version ID of the entity

        Returns:
            (JsonResponse): a JSON-encoded `HttpResponse` specifying the status of this request and any _assoc._ messages and/or data
        """
        # Attempt to resolve entity
        entity = GenericEntity.objects.filter(pk=pk)
        entity = entity.first() if entity.exists() else None

        historical_entity = entity.history.filter(history_id=history_id) if entity is not None else None
        historical_entity = historical_entity.first() if historical_entity is not None and historical_entity.exists() else None

        if entity is None or historical_entity is None:
            logger.warning(
                'Failed <Publish> POST request, unable to resolve Found<live: %s, hist: %s> for Args<id: %s, ver: %s>' % (
                    str(entity is not None),
                    str(historical_entity is not None),
                    str(pk),
                    str(history_id),
                )
            )

            return JsonResponse({
                'message': render_to_string('clinicalcode/error.html', {}, request),
                'form_is_valid': False,
            })

        # Check if entity could be published if not show error
        is_published = permission_utils.check_if_published(GenericEntity, pk, history_id)
        checks = publish_utils.check_entity_to_publish(request, pk, history_id)
        # if not is_published:
        #     checks = publish_utils.check_entity_to_publish(request, pk, history_id)

        if not checks['allowed_to_publish'] or is_published:
            return JsonResponse({
                'message': render_to_string('clinicalcode/error.html', {}, request),
                'form_is_valid': False,
            })

        # Attempt to construct response
        data = dict()
        try:
            is_moderator = checks.get('is_moderator', False)
            is_publisher = checks.get('is_publisher', False)
            is_lastapproved = checks.get('is_lastapproved', False)
            approval_status = checks.get('approval_status', False)
            org_user_managed = checks.get('org_user_managed', False)
            has_other_pending = checks.get('other_pending', False)

            with transaction.atomic():
                # Check if publishable
                if self.condition_to_publish(checks, is_published):
                    send_review_mail = True

                    if org_user_managed:
                        # Publish if org moderator
                        if is_moderator:
                            published_entity, _ = PublishedGenericEntity.objects.update_or_create(
                                entity=entity,
                                entity_history_id=history_id,
                                defaults={
                                    'moderator_id': request.user.id,
                                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                                },
                                create_defaults={
                                    'created_by_id': entity.created_by.id,
                                    'moderator_id': request.user.id,
                                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                                }
                            )
                    else:
                        # Check if moderator first and if was already approved to filter by only approved entitys
                        if is_moderator:
                            if is_lastapproved:
                                self.last_approved_publish(request, pk, history_id)
                            else:
                                send_review_mail = False
                                self.moderator_publish(request, pk, history_id, checks, data)

                        # Publish immediately if permitted
                        if is_publisher and not is_moderator:
                            published_entity, _ = PublishedGenericEntity.objects.update_or_create(
                                entity=entity,
                                entity_history_id=history_id,
                                defaults={
                                    'moderator_id': request.user.id,
                                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                                },
                                create_defaults={
                                    'moderator_id': request.user.id,
                                    'created_by_id': entity.created_by.id,
                                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                                }
                            )

                        # Publish if was already published
                        if is_lastapproved and not is_moderator and not is_publisher:
                            self.last_approved_publish(request, pk, history_id)

                        # Approve other pending entity if available to publish
                        if has_other_pending:
                            published_entity = PublishedGenericEntity.objects.filter(
                                entity_id=entity.id,
                                approval_status=constants.APPROVAL_STATUS.PENDING.value
                            )

                            to_update = []
                            for en in published_entity:
                                en.modified = make_aware(datetime.now())
                                en.moderator_id = request.user.id
                                en.approval_status = constants.APPROVAL_STATUS.APPROVED.value
                                to_update.append(en)
                            PublishedGenericEntity.objects.bulk_update(to_update, ['approval_status', 'moderator_id', 'modified'])

                    data['form_is_valid'] = True
                    data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
                    data['latest_history_ID'] = history_id
                    data['entity_name_requested'] = historical_entity.name

                    # Show state message to the client side and send email
                    if send_review_mail:
                        publish_utils.form_validation(request, data, pk, history_id, entity, checks)

                # Check if moderator and current entity is in pending state
                elif approval_status == constants.APPROVAL_STATUS.PENDING and is_moderator:
                    self.moderator_publish(request, pk, history_id, checks, data)

                # Check if entity declined and user is moderator to review again
                elif approval_status == constants.APPROVAL_STATUS.REJECTED and is_moderator:
                    self.moderator_publish(request, pk, history_id, checks, data)

        except Exception as e:
            logger.warning('Failed <Publish> POST request with error: %s' % (str(e),))

            data['message'] = render_to_string('clinicalcode/error.html', {}, request)
            data['form_is_valid'] = False

        finally:
            registrable = doi_utils.is_publish_target_registrable(
                form_valid=data.get('form_is_valid', False),
                approval_status=data.get('approval_status', -1)
            )

            if registrable:
                doi_utils.publish_doi_task(historical_entity, timeout=0.5)

        return JsonResponse(data)

    def condition_to_publish(self, checks, is_published):
        """
        Determines whether the conditions have been met to publish the entity.

        Args:
            checks       (Dict[Str,Any]): conditional checks computed for the entity of interest
            is_published          (bool): specifies whether this entity has been published

        Returns:
            (bool): Resolves to `True` if the entity is unpublished AND either (a) it has been approved OR (b) it is publishable and has not yet been recorded in the DB
        """
        approval_status = checks.get('approval_status', False) if isinstance(checks, dict) else False
        is_unknown_status = approval_status is None or (isinstance(approval_status, bool) and not approval_status)
        return (
            not is_published
            and (
                (checks['approval_status'] == constants.APPROVAL_STATUS.APPROVED)
                or (checks['allowed_to_publish'] and is_unknown_status)
            )
        )

    def moderator_publish(self, request, pk, history_id, conditions, data):
        """
        Attempts to approve the publication of an `entity` by either updating or creating an _assoc._ :model:`PublishedGenericEntity`

        Args:
            request      (HttpRequest): the HTTP request context
            pk                   (str): the ID of the entity to publish
            history_id           (int): the version id of the entity to publish
            conditions (Dict[Str,Any]): conditional checks computed for the entity of interest
            data       (Dict[Str,Any]): computed client & email data _assoc._ with this request

        Returns:
            (PublishedGenericEntity): the :model:`PublishedGenericEntity` assoc. with this moderator approval request        
        """
        entity = GenericEntity.objects.get(pk=pk)
        historical_entity = entity.history.get(history_id=history_id)

        # Approve previous request
        if conditions['approval_status'] == constants.APPROVAL_STATUS.PENDING:
            published_entity, _ = PublishedGenericEntity.objects.update_or_create(
                entity=entity,
                entity_history_id=history_id,
                approval_status=constants.APPROVAL_STATUS.PENDING.value,
                defaults={
                    'modified': make_aware(datetime.now()),
                    'moderator_id': request.user.id,
                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                },
                create_defaults={
                    'moderator_id': request.user.id,
                    'created_by_id': entity.created_by.id,
                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                }
            )

            data['form_is_valid'] = True
            data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
            data['entity_name_requested'] = historical_entity.name

            # Update client info
            publish_utils.form_validation(request, data, pk, history_id, entity, conditions)

        # Approve previously rejected request
        elif conditions['approval_status'] == constants.APPROVAL_STATUS.REJECTED:
            # Filter by declined ws
            published_entity, _ = PublishedGenericEntity.objects.update_or_create(
                entity=entity,
                entity_history_id=history_id,
                approval_status=constants.APPROVAL_STATUS.REJECTED.value,
                defaults={
                    'modified': make_aware(datetime.now()),
                    'moderator_id': request.user.id,
                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                },
                create_defaults={
                    'moderator_id': request.user.id,
                    'created_by_id': entity.created_by.id,
                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                }
            )

            # Check if other pending exist to approve this ws automatically
            if conditions['other_pending']:
                published_entity = PublishedGenericEntity.objects.filter(
                    entity_id=entity.id,
                    approval_status=constants.APPROVAL_STATUS.PENDING.value
                )

                to_update = []
                for en in published_entity:
                    en.modified = make_aware(datetime.now())
                    en.moderator_id = request.user.id
                    en.approval_status = constants.APPROVAL_STATUS.APPROVED.value
                    to_update.append(en)
                PublishedGenericEntity.objects.bulk_update(to_update, ['approval_status', 'moderator_id', 'modified'])

            data['form_is_valid'] = True
            data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
            data['entity_name_requested'] = historical_entity.name

            # Update client info
            publish_utils.form_validation(request, data, pk, history_id, entity, conditions)

        # Otherwise, update or create an approved record
        else:
            published_entity, _ = PublishedGenericEntity.objects.update_or_create(
                entity=entity,
                entity_history_id=history_id,
                defaults={
                    'moderator_id': request.user.id,
                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                },
                create_defaults={
                    'moderator_id': request.user.id,
                    'created_by_id': entity.created_by.id,
                    'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
                }
            )

            data['form_is_valid'] = True
            data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
            data['entity_name_requested'] = historical_entity.name

            # Update client info
            publish_utils.form_validation(request, data, pk, history_id, entity, conditions)

        return published_entity
            
    def last_approved_publish(self, request, pk, history_id):
        """
        Approves a new publication request following a previously moderated entity's approval.

        Args:
            request      (HttpRequest): the HTTP request context
            pk                   (str): the ID of the entity to publish
            history_id           (int): the version id of the entity to publish

        Returns:
            (PublishedGenericEntity): the :model:`PublishedGenericEntity` assoc. with this moderator approval request        
        """
        last_moderated = PublishedGenericEntity.objects.filter(
            entity_id=pk,
            approval_status=constants.APPROVAL_STATUS.APPROVED.value
        ) \
            .first()

        return PublishedGenericEntity.objects.update_or_create(
            entity_id=pk,
            entity_history_id=history_id,
            defaults={
                'modified': make_aware(datetime.now()),
                'moderator_id': last_moderated.moderator.id,
                'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
            },
            create_defaults={
                'moderator_id': last_moderated.moderator.id,
                'created_by_id': request.user.id,
                'approval_status': constants.APPROVAL_STATUS.APPROVED.value,
            }
        )[0]

class RequestPublish(LoginRequiredMixin, permission_utils.HasAccessToViewGenericEntityCheckMixin, TemplateResponseMixin, View):
    """
    View to manage requests by user(s) to publish an entity.

    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms;
        - This has been temporarily documented & updated by @js/is in the meantime but this will require reimplementation.
    """
    model = GenericEntity
    template_name = 'clinicalcode/generic_entity/publish/request_publish.html'

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self, request, pk, history_id):
        """
        Handle GET requests by users initiating the publication request process by opening the `js/entityPublish.js` modal

        Args:
            request (HttpRequest): the HTTP request context
            pk              (str): the ID of the entity
            history_id      (int): the version ID of the entity

        Returns:
            (JsonResponse): a JSON-encoded `HttpResponse` specifying entity & publication data required to initiate the request process
        """
        #get additional checks in case if ws is deleted/approved etc
        checks = publish_utils.check_entity_to_publish(request, pk, history_id)
        checks['entity_history_id'] = history_id
        checks['entity_id'] = pk

        return JsonResponse(checks, safe=False)
    
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def post(self,request, pk, history_id):
        """
        Handle POST requests by users attempting to request the publication of an entity (pending)

        Args:
            request (HttpRequest): the HTTP request context
            pk              (str): the ID of the entity
            history_id      (int): the version ID of the entity

        Returns:
            (JsonResponse): a JSON-encoded `HttpResponse` specifying the status of this request and any _assoc._ messages and/or data
        """
        checks = publish_utils.check_entity_to_publish(request, pk, history_id)
        is_published = permission_utils.check_if_published(GenericEntity, pk, history_id)

        pub_status = checks['approval_status']
        not_pubbed = pub_status is None or (isinstance(pub_status, bool) and not pub_status)

        data = dict()
        if not checks['allowed_to_publish'] or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {}, request)
            return JsonResponse(data)

        try:
            # (allowed to permit) AND (ws not published) AND (approval_status not in database) AND (user not moderator)
            if checks['allowed_to_publish'] and not is_published and not_pubbed and not checks['is_moderator']:
                entity = GenericEntity.objects.get(pk=pk)

                # start a transaction
                with transaction.atomic():
                    PublishedGenericEntity.objects.update_or_create(
                        entity=entity,
                        entity_history_id=history_id,
                        approval_status=constants.APPROVAL_STATUS.PENDING.value,
                        defaults={
                            'modified': make_aware(datetime.now()),
                            'approval_status': constants.APPROVAL_STATUS.PENDING.value,
                        },
                        create_defaults={
                            'created_by_id': request.user.id,
                            'approval_status': constants.APPROVAL_STATUS.PENDING.value,
                        }
                    )

                    data['form_is_valid'] = True
                    data['approval_status'] = constants.APPROVAL_STATUS.PENDING
                    data['entity_name_requested'] = entity.history.get(history_id=history_id).name

                    data = publish_utils.form_validation(request, data, pk, history_id, entity, checks)
        except Exception as e:
            logger.warning('Failed <PublishRequest> POST with error: %s' % (str(e),))

            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {}, request)

        return JsonResponse(data)
