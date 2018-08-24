from flask import current_app
from collections import OrderedDict
import random

from ..extensions import cache
from ..campaign.constants import (SEGMENT_BY_LOCATION,
    INCLUDE_SPECIAL_BEFORE, INCLUDE_SPECIAL_AFTER,
    INCLUDE_SPECIAL_ONLY, INCLUDE_SPECIAL_FIRST,
)

def validate_location(location, campaign, cache=cache):
    campaign_data = campaign.get_campaign_data(cache)
    validated_location = campaign_data.data_provider.get_location(campaign.locate_by, location)
    return validated_location

def locate_targets(location, campaign, skip_special=False, cache=cache):
    """
    Convenience method to get targets for location in a given campaign.
    Assumes campaign.segment_by == SEGMENT_BY_LOCATION
    If skip_special is true, will only return location-based targets
    @return  list of target uids
    """

    if campaign.segment_by and campaign.segment_by != SEGMENT_BY_LOCATION:
        current_app.logger.error('Called locate_targets on campaign where segment_by=%s (%s)' % (campaign.segment_by, campaign.id))
        return []

    campaign_data = campaign.get_campaign_data(cache)
    location_targets = campaign_data.get_targets_for_campaign(location, campaign)
    special_targets = [t.uid for t in campaign.target_set]

    if skip_special:
        return location_targets

    if campaign.target_set:
        if campaign.target_ordering == 'shuffle':
            random.shuffle(special_targets)

        if campaign.include_special == INCLUDE_SPECIAL_BEFORE:
            # include special targets before location targets
            combined = special_targets + location_targets
            return list(OrderedDict.fromkeys(combined))
        elif campaign.include_special == INCLUDE_SPECIAL_AFTER:
            # include special targets after location targets
            combined = location_targets + special_targets
            return list(OrderedDict.fromkeys(combined))
        elif campaign.include_special == INCLUDE_SPECIAL_ONLY:
            # find overlap between special_targets and location_targets
            # use nested loops instead of set intersections, so we can match string startswith
            # and maintain ordering
            overlap_list = list()
            for l in location_targets:
                for t in special_targets:
                    if t.startswith(l):
                        if t not in overlap_list:
                            overlap_list.append(t)

            if campaign.target_ordering == 'shuffle':
                random.shuffle(overlap_list)
            return overlap_list
        elif campaign.include_special == INCLUDE_SPECIAL_FIRST:
            # if location target is in special targets, put it first
            # then include other special targets
            first_targets = list()

            for l in location_targets:
                for t in special_targets:
                    if t.startswith(l):
                        if t not in first_targets:
                            first_targets.insert(0, t)
            
            if campaign.target_ordering == 'shuffle':
                random.shuffle(special_targets)
            combined = first_targets + special_targets
            return list(OrderedDict.fromkeys(combined))
        else:
            return special_targets
    else:
        return location_targets
