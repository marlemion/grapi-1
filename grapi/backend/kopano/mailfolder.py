# SPDX-License-Identifier: AGPL-3.0-or-later

from .utils import (
    _server_store, _folder, HTTPBadRequest, experimental
)
from .message import MessageResource
from .folder import FolderResource


class DeletedMailFolderResource(FolderResource):
    fields = {
        '@odata.type': lambda folder: '#microsoft.graph.mailFolder',  # TODO
        'id': lambda folder: folder.entryid,
        '@removed': lambda folder: {'reason': 'deleted'}  # TODO soft deletes
    }


@experimental
class MailFolderResource(FolderResource):
    fields = FolderResource.fields.copy()
    fields.update({
        'parentFolderId': lambda folder: folder.parent.entryid,
        'displayName': lambda folder: folder.name,
        'unreadItemCount': lambda folder: folder.unread,
        'totalItemCount': lambda folder: folder.count,
        'childFolderCount': lambda folder: folder.subfolder_count,
    })

    relations = {
        'childFolders': lambda folder: (folder.folders, MailFolderResource),
        'messages': lambda folder: (folder.items, MessageResource)  # TODO event msgs
    }

    deleted_resource = DeletedMailFolderResource
    container_classes = (None, 'IPF.Note')

    def handle_get_childFolders(self, req, resp, store, folderid):
        data = _folder(store, folderid)

        data = self.generator(req, data.folders, data.subfolder_count_recursive)
        self.respond(req, resp, data)

    def handle_get_messages(self, req, resp, store, folderid):
        data = _folder(store, folderid)

        data = self.folder_gen(req, data)
        self.respond(req, resp, data, MessageResource.fields)

    def handle_get(self, req, resp, store, folderid):
        if folderid:
            if folderid == 'delta':
                self._handle_get_delta(req, resp, store=store)
            else:
                self._handle_get_with_folderid(req, resp, store=store, folderid=folderid)

    def _handle_get_delta(self, req, resp, store):
        req.context['deltaid'] = '{folderid}'
        self.delta(req, resp, store=store)

    def _handle_get_with_folderid(self, req, resp, store, folderid):
        data = _folder(store, folderid)
        self.respond(req, resp, data)

    def on_get(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_get

        elif method == 'childFolders':
            handler = self.handle_get_childFolders

        elif method == 'messages':
            handler = self.handle_get_messages

        else:
            raise HTTPBadRequest("Unsupported mailfolder segment '%s'" % method)

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store=store, folderid=folderid)

    def handle_post_messages(self, req, resp, store, folderid):
        folder = _folder(store, folderid)
        fields = self.load_json(req)
        item = self.create_message(folder, fields, MessageResource.set_fields)
        self.respond(req, resp, item, MessageResource.fields)

    def handle_post_childFolders(self, req, resp, store, folderid):
        child = folder.create_folder(fields['displayName'])  # TODO exception on conflict
        self.respond(req, resp, child, MailFolderResource.fields)

    def handle_post_copy(self, req, resp, store, folderid):
        this._handle_post_copyOrMove(move=False)

    def handle_post_move(self, req, resp, store, folderid):
        this._handle_post_copyOrMove(move=True)

    def _handle_post_copyOrMove(self, req, resp, store, folderid, move=False):
        fields = self.load_json(req)
        to_folder = store.folder(entryid=fields['destinationId'].encode('ascii'))  # TODO ascii?
        if not move:
            folder.parent.copy(folder, to_folder)
        else:
            folder.parent.move(folder, to_folder)

    def on_post(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if method == 'messages':
            handler = this.handle_post_messages

        elif method == 'childFolders':
            handler = this.handle_post_childFolders

        elif method == 'copy':
            handler = this.handle_post_copy

        elif method == 'move':
            handler = this.handle_post_move

        elif method:
            raise HTTPBadRequest("Unsupported mailfolder segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in mailfolder")

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store, folderid)
