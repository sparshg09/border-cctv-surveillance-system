import cv2
import numpy as np


class PolygonZoneManager:

    def __init__(
        self,
        restricted_polygon,
        warning_polygon=None,
        fps=30,
        loiter_seconds=5
    ):

        self.restricted_polygon = (
            restricted_polygon
        )

        self.warning_polygon = (
            warning_polygon
            if warning_polygon
            else []
        )

        self.fps = fps

        self.loiter_frames = int(
            fps *
            loiter_seconds
        )


        # Person encounter state
        self.people = {}


    # =====================================================
    # POINT INSIDE POLYGON
    # =====================================================

    def point_inside(
        self,
        point,
        polygon
    ):

        if (
            polygon is None
            or
            len(polygon) < 3
        ):

            return False


        contour = np.array(
            polygon,
            dtype=np.int32
        )


        result = cv2.pointPolygonTest(

            contour,

            (
                float(point[0]),
                float(point[1])
            ),

            False
        )


        return (
            result >= 0
        )


    # =====================================================
    # GET ZONE
    # =====================================================

    def get_zone(
        self,
        point
    ):

        if self.point_inside(
            point,
            self.restricted_polygon
        ):

            return "RESTRICTED"


        if self.point_inside(
            point,
            self.warning_polygon
        ):

            return "WARNING"


        return "SAFE"


    # =====================================================
    # UPDATE PERSON
    # =====================================================

    def update_person(
        self,
        encounter_id,
        foot_point,
        frame_number
    ):

        zone = self.get_zone(
            foot_point
        )


        if (
            encounter_id
            not in
            self.people
        ):

            self.people[
                encounter_id
            ] = {

                "zone":
                    zone,

                "restricted_start":
                    (
                        frame_number
                        if zone ==
                        "RESTRICTED"
                        else None
                    ),

                "intrusion_alerted":
                    False,

                "loiter_alerted":
                    False
            }


        state = (
            self.people[
                encounter_id
            ]
        )


        previous_zone = (
            state[
                "zone"
            ]
        )


        entered_restricted = False

        exited_restricted = False

        loiter_event = False


        # =================================================
        # ENTER RESTRICTED AREA
        # =================================================

        if (
            zone ==
            "RESTRICTED"
        ):

            if (
                previous_zone
                !=
                "RESTRICTED"
            ):

                entered_restricted = True

                state[
                    "restricted_start"
                ] = frame_number

                state[
                    "intrusion_alerted"
                ] = True


            if (
                state[
                    "restricted_start"
                ]
                is None
            ):

                state[
                    "restricted_start"
                ] = frame_number


            restricted_frames = (

                frame_number

                -

                state[
                    "restricted_start"
                ]
            )


            if (
                restricted_frames
                >=
                self.loiter_frames
                and
                not state[
                    "loiter_alerted"
                ]
            ):

                state[
                    "loiter_alerted"
                ] = True

                loiter_event = True


        # =================================================
        # LEAVE RESTRICTED AREA
        # =================================================

        else:

            if (
                previous_zone
                ==
                "RESTRICTED"
            ):

                exited_restricted = True


            state[
                "restricted_start"
            ] = None


            state[
                "loiter_alerted"
            ] = False


        state[
            "zone"
        ] = zone


        return {

            "zone":
                zone,

            "previous_zone":
                previous_zone,

            "entered_restricted":
                entered_restricted,

            "exited_restricted":
                exited_restricted,

            "loiter_event":
                loiter_event,

            "foot_point":
                foot_point
        }