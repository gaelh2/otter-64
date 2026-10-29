#ifndef LIBPL_RHDC_
#define LIBPL_RHDC_

#include "libpl-types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*! @name libpl_try_get_rhdc_avatar_async option flags (bitflag- can combine options with bitwise or)
 * @{
 */
#define LIBPL_AVATAR_DITHER			0x0001 /*!< If this flag is provided, Floyd-Steinberg dithering will be used when converting the avatar to the RGBA16 format. (no effect if the depth is 32) */
#define LIBPL_AVATAR_NO_FILTERING	0x0002 /*!< If this flag is provided, the avatar will be resized to the requested size without using any filtering. Otherwise, if this flag is not provided, the avatar will be scaled using bilinear filtering. */
#define LIBPL_AVATAR_NO_ALPHA		0x0004 /*!< If this flag is provided, any alpha transparency in the image will be removed and replaced with black. */
#define LIBPL_AVATAR_ZOOM   		0x0008 /*!< If this flag is provided, an avatar that is not square will be zoomed in and the sides cropped to fit in a square box. Otherwise, if this flag is not provided, the avatar will be given a border of transparent (or black if the LIBPL_AVATAR_NO_ALPHA flag is provided) pixels on the sides. */
/*! @} */

/*! @defgroup page_rhdc Romhacking.com Commands
 * @{
 */

/*! Returns a pointer to a null-terminated string containing the username of the
 * current RHDC user, or @c NULL if the user has not enabled RHDC integration.
 * The pointer is only valid until you next call a libpl function.
 * 
 * @return A pointer to a null-terminated string containing the username, or @c NULL on an error. \n
 * The returned pointer is only valid until you next invoke a libpl function.
 * 
 * @since LPL_ABI_VERSION_3
 */
const char *libpl_get_my_rhdc_username();

/*! Fetches the avatar for the given username in RHDC as a 32x32 pixel image in
 * RGB16 format and stores it at the provided memory address. If the operation
 * failed or the user is not found, the provided memory is not modified, and the
 * function returns a non-zero value. Otherwise, returns 0.
 * @deprecated Use @ref libpl_try_get_rhdc_avatar_async instead
 * 
 * @bug This function fails with return value 3 for non-square avatars on
 * Parallel Launcher versions prior to 7.10.0 (LPL_ABI_VERSION_7)
 * @bug This function returns only a black image on version 7.10.0.
 * This bug is fixed in version 7.10.1, released a day later.
 * 
 * @param[in] username A null-terminated string containing the username or userId
 * @param[out] dest A buffer of at least 2048 bytes that the avatar will be written to
 * 
 * @return Returns 0 on success, or a non-zero value otherwise \n
 * A return value of 1 indicates that the user was not found or has no avatar \n
 * A return value of 2 indicates a network error (can retry) \n
 * A return value of 3 indicates an image processing error \n
 * A return value of 4 indicates that you are being rate limited (can retry)
 * 
 * @async
 * 
 * @since LPL_ABI_VERSION_3
 */
int libpl_get_rhdc_avatar_16_async( const char *username, void *dest );

/*! Fetches the avatar for the given username in RHDC as a 32x32 pixel image in
 * RGBA32 format and stores it at the provided memory address. If the operation
 * failed or the user is not found, the provided memory is not modified, and the
 * function returns a non-zero value. Otherwise, returns 0.
 * @deprecated Use @ref libpl_try_get_rhdc_avatar_async instead
 * 
 * @bug This function fails with return value 3 for non-square avatars on
 * Parallel Launcher versions prior to 7.10.0 (LPL_ABI_VERSION_7)
 * @bug This function is broken in emulator core version 2.14.0 and is fixed in 2.14.1
 * 
 * @param[in] username A null-terminated string containing the username or userId
 * @param[out] dest A buffer of at least 4096 bytes that the avatar will be written to
 * 
 * @return Returns 0 on success, or a non-zero value otherwise \n
 * A return value of 1 indicates that the user was not found or has no avatar \n
 * A return value of 2 indicates a network error (can retry) \n
 * A return value of 3 indicates an image processing error \n
 * A return value of 4 indicates that you are being rate limited (can retry)
 * 
 * @async
 * 
 * @since LPL_ABI_VERSION_3
 */
int libpl_get_rhdc_avatar_32_async( const char *username, void *dest );

/*! Fetches the avatar for the given username in RHDC and stores it at the
 * provided memory address. If the operation failed or the user is not found,
 * the provided memory is not modified, the function returns FALSE, and
 * @ref lpl_status is set to a non-zero value.
 * 
 * @param[in] username A null-terminated string containing the username or userId
 * @param[out] dest A buffer that the avatar will be written to. The required buffer sizes are:
 * - @ref 512 bytes for size 16 and depth 16
 * - @ref 1024 bytes for size 16 and depth 32
 * - @ref 2048 bytes for size 32 and depth 16
 * - @ref 4096 bytes for size 32 and depth 32
 * - @ref 8192 bytes for size 64 and depth 16
 * - @ref 16384 bytes for size 64 and depth 32
 * @param[in] size The width and height of the image in pixels. Must be one of 16, 32, or 64.
 * @param[in] depth The colour depth of the image. Must be 16 or 32.
 * @param[in] options Optional additional options (see above)
 * 
 * @return Returns TRUE on success, sets @ref lpl_status to one of the following values on an error:
 * - 0x500 - The async operation is not finished yet. Call it again with the same arguments later to check on the result.
 * - 1 - The user was not found or has no avatar
 * - 2 - A network error occurred (can retry)
 * - 3 - An image processing error occurred
 * - 4 - You are being rate limited (can retry)
 * - 0x201 or 0x200 - Invalid arguments
 * - 0x300 - The connection to Parallel Launcher was lost
 * 
 * @async
 * 
 * @since LPL_ABI_VERSION_7
 */
bool32_t libpl_try_get_rhdc_avatar_async( const char *username, void *dest, unsigned char size, unsigned char depth, unsigned short options );

/*! @} */

#ifdef __cplusplus
}
#endif

#endif
