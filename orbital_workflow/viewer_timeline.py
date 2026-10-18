"""Read completed acquisition ownership without loading recursive Episode logs."""
import json
from pathlib import Path


def load_timeline(directory, rows):
    directory = Path(directory)
    by_id = {row['id']: row for row in rows}
    episodes, warnings = {}, []
    for path in (directory / 'episode-store/episodes').glob('*/manifest.json'):
        try:
            value = json.loads(path.read_text())
            episodes[value['episode_id']] = value
        except (OSError, ValueError, KeyError) as error:
            warnings.append({'file':str(path), 'error':type(error).__name__})
    # Ownership is published after its observation index entries. Immutable
    # ownership file timestamps retain the original publication order on replay.
    paths = list((directory / 'episode-store/ownership').glob('*/*.json'))
    published = []
    for path in paths:
        try:
            published.append((path.stat().st_mtime_ns, str(path), path))
        except OSError as error:
            warnings.append({'file':str(path), 'error':type(error).__name__})
    timeline = []
    for acquisition, (_, _, path) in enumerate(sorted(published), 1):
        try:
            observations = json.loads(path.read_text())['observations']
            if any(identity not in by_id for identity in observations):
                raise ValueError('Observation metadata publication is pending')
            episode_id, unit_id = path.parent.name, path.stem
            episode = episodes.get(episode_id, {})
            structural_path = episode.get('path', [])
            investigation = None
            if len(structural_path)>1 and structural_path[1][1].startswith('unit-'):
                investigation = int(structural_path[1][1].split('-')[1])+1
            for position, identity in enumerate(observations):
                row = by_id[identity]
                origin = row.get('origin') or {}
                if investigation is None and row['episode_id']==episode_id:
                    investigation = origin.get('investigation')
                timeline.append({
                    'key':unit_id+':'+str(position), 'observation_id':identity,
                    'episode_id':episode_id, 'unit_id':unit_id,
                    'acquisition':acquisition, 'position':position+1,
                    'observation_count':len(observations), 'investigation':investigation,
                    'label':origin.get('action') if row.get('unit_id')==unit_id else 'Revisited saved observation',
                })
        except (OSError, ValueError, KeyError) as error:
            warnings.append({'file':str(path), 'error':type(error).__name__})
    # Index entries can appear milliseconds before the ownership publication.
    # Show them while waiting; replace these temporary keys on the next refresh.
    known = {entry['observation_id'] for entry in timeline}
    for row in rows:
        if row['id'] not in known:
            origin = row.get('origin') or {}
            timeline.append({'key':row['id'], 'observation_id':row['id'],
                'episode_id':row['episode_id'], 'unit_id':row['unit_id'],
                'acquisition':None, 'position':1, 'observation_count':1,
                'investigation':origin.get('investigation'), 'label':origin.get('action')})
    return timeline, warnings
