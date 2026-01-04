import json
from pathlib import Path

import sh

from daily.utils import hc_ping, logger
from shared.config import get_config_smarthealthc


def smarthealthc():
    """Like https://github.com/zzdroide/borgmatic/blob/master/hooks.d/helpers/smart_check_disk.sh"""

    for hc_url, disk in get_config_smarthealthc():
        action, msg = process_disk(disk)

        if action == 'log':
            logger.warning(msg)
        elif action == 'fail':
            logger.error(msg)

        hc_ping(f'{hc_url}/{action}', msg)


def process_disk(disk: str):
    if not Path(disk).is_block_device():
        return 'log', f'Disk {disk} is not present'

    try:
        info = sh.sudo('/usr/sbin/smartctl', '-HA', '--json=c', disk, _ok_code=range(256))
        data = json.loads(info)
    except Exception as e:
        return 'log', f'Failed to get smart info for {disk}: {e}'

    if data.get('json_format_version') != [1, 0]:
        return 'log', "json_format_version doesn't match"

    if not data.get('smart_status', {}).get('passed'):
        return 'fail', f'Drive self-assessment is bad for {disk}'

    # https://www.backblaze.com/blog/what-smart-stats-indicate-hard-drive-failures/
    backblaze_attrs = {5, 187, 188, 197, 198}
    for attr in data.get('ata_smart_attributes', {}).get('table', []):
        if attr.get('id') in backblaze_attrs and attr.get('raw', {}).get('value', 0) != 0:
            return 'fail', f"Attribute {attr['id']} is {attr['raw']['value']} (greater than 0) for {disk}"

    return '0', None  # Success
