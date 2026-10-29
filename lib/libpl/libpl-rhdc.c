#include "libpl-rhdc.h"

#include <string.h>
#include "libpl-internal.h"
#include "libpl-common.h"
#include "libpl-util.h"

struct lpl_rhdc_avatar_request {
	unsigned char size;
	unsigned char depth;
	unsigned short options;
	char username[];
};

const char *libpl_get_my_rhdc_username() {
	const libpl_response *response = libpl_query_basic( 0x0200 );
	return response->status ? NULL : (const char*)response->payload;
}

int libpl_get_rhdc_avatar_16_async( const char *username, void *dest ) {
	const libpl_response *response = libpl_query_string( 0x0201, username );
	if( !response->status ) memcpy( dest, response->payload, response->payload_size );
	return (int)response->status;
}

int libpl_get_rhdc_avatar_32_async( const char *username, void *dest ) {
	const libpl_response *response = libpl_query_string( 0x0202, username );
	if( !response->status ) memcpy( dest, response->payload, response->payload_size );
	return (int)response->status;
}

bool32_t libpl_try_get_rhdc_avatar_async( const char *username, void *dest, unsigned char size, unsigned char depth, unsigned short options ) {
	struct lpl_rhdc_avatar_request *payload = (struct lpl_rhdc_avatar_request*)libpl_payload_start();
	payload->size = size;
	payload->depth = depth;
	payload->options = options;
	const unsigned short usernameLen = lpl_strncpy( payload->username, username, 0xFFF8 );
	const libpl_response *response = libpl_payload_send( 0x0203, usernameLen + 4 );
	if( response->status == 0 ) {
		memcpy( dest, response->payload, response->payload_size );
		return TRUE;
	}
	return FALSE;
}
