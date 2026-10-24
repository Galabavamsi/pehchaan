package `in`.humanslop.pehchaan

import android.Manifest
import android.content.Context
import android.net.Uri
import android.provider.ContactsContract

/** On-device contact match (SPEC §6): the contact list never leaves the phone, only the yes/no answer. */
object ContactCheck {
    /** null when READ_CONTACTS isn't granted, so the API can tell "not checked" from "not a contact". */
    fun inContacts(c: Context, number: String): Boolean? {
        if (!CallMonitor.has(c, Manifest.permission.READ_CONTACTS)) return null
        val uri = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number))
        return runCatching {
            c.contentResolver.query(uri, arrayOf(ContactsContract.PhoneLookup._ID), null, null, null)
                ?.use { it.count > 0 } ?: false
        }.getOrNull()
    }
}
