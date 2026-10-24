package `in`.humanslop.pehchaan

import android.Manifest
import android.content.Context
import android.net.Uri
import android.provider.ContactsContract

/**
 * On-device contact match (SPEC §6): the contact list never leaves the phone. The API gets only yes/no; the saved
 * name ("Mummy", "Vamsi beta") is shown on this phone's own screen, like the dialer does, and is never sent.
 */
object ContactCheck {
    data class Match(val inContacts: Boolean?, val name: String?)

    /** inContacts is null when READ_CONTACTS isn't granted, so the API can tell "not checked" from "not a contact". */
    fun lookup(c: Context, number: String): Match {
        if (!CallMonitor.has(c, Manifest.permission.READ_CONTACTS)) return Match(null, null)
        val uri = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number))
        return runCatching {
            c.contentResolver.query(uri, arrayOf(ContactsContract.PhoneLookup.DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) Match(true, it.getString(0)) else Match(false, null)
            } ?: Match(false, null)
        }.getOrDefault(Match(null, null))
    }

    fun inContacts(c: Context, number: String): Boolean? = lookup(c, number).inContacts
}
