import json
from pathlib import Path

import sh

from daily.utils import hc_ping, logger
from shared.config import get_config_smarthealthc


def smarthealthc():
    """Like https://github.com/zzdroide/borgmatic/blob/master/hooks.d/helpers/smart_check_disk.sh"""

    for hc_url, disk in get_config_smarthealthc():
        action, msg = process_disk(disk)
        hc_ping(f'{hc_url}/{action}', msg)


def process_disk(disk: str):
    if not Path(disk).is_block_device():
        msg = f'Disk {disk} is not present'
        logger.warning(msg)
        return '/log', msg

    try:
        info = sh.sudo('/usr/sbin/smartctl', '-HA', '--json=c', disk, _ok_code=range(256))
        data = json.loads(info)
    except Exception as e:
        msg = f'Failed to get smart info for {disk}: {e}'
        logger.warning(msg)
        return '/log', msg

    if data.get('json_format_version') != [1, 0]:
        msg = "json_format_version doesn't match"
        logger.warning(msg)
        return '/log', msg

    if not data.get('smart_status', {}).get('passed'):
        msg = f'Drive self-assessment is bad for {disk}'
        logger.error(msg)
        return '/fail', msg

    # https://www.backblaze.com/blog/what-smart-stats-indicate-hard-drive-failures/
    backblaze_attrs = {5, 187, 188, 197, 198}
    for attr in data.get('ata_smart_attributes', {}).get('table', []):
        if attr.get('id') in backblaze_attrs and attr.get('raw', {}).get('value', 0) != 0:
            msg = f"Attribute {attr['id']} is {attr['raw']['value']} (greater than 0)"
            logger.error(msg)
            return '/fail', msg

    return '0', None  # Success
