import math
from datetime import datetime


class PersonMonitor:

    def __init__(
        self,
        video_width,
        video_height,
        fps,
        restricted_x
    ):

        self.width = video_width
        self.height = video_height
        self.fps = fps

        self.restricted_x = restricted_x


        # =====================================================
        # CONFIRMATION SETTINGS
        # =====================================================

        # A person must remain detected for enough frames   
        # before we register them as a confirmed encounter.
        self.MIN_CONFIRM_FRAMES = 3

        # Ignore tiny distant detections that often cause
        # unstable temporary IDs.
        self.MIN_BOX_AREA = 500


        # =====================================================
        # RECONNECTION SETTINGS
        # =====================================================

        # Keep recently lost encounters available for
        # reconnection for a short period.
        self.RECONNECT_SECONDS = 2.5

        self.RECONNECT_FRAMES = int(
            self.fps *
            self.RECONNECT_SECONDS
        )


        # Base allowed distance between a new raw track
        # and a recently lost encounter.
        self.BASE_RECONNECT_DISTANCE = (
            max(
                self.width,
                self.height
            )
            *
            0.07
        )


        # Hard maximum spatial reconnect distance.
        self.MAX_RECONNECT_DISTANCE = (
            max(
                self.width,
                self.height
            )
            *
            0.14
        )


        # Minimum similarity in bounding-box size.
        self.MIN_SIZE_SIMILARITY = 0.45


        # Maximum final matching score.
        # Smaller = stricter.
        self.MAX_MATCH_SCORE = 0.85


        # =====================================================
        # LOITERING
        # =====================================================

        self.LOITER_SECONDS = 5.0

        self.LOITER_FRAMES = max(
            1,
            int(
                self.fps *
                self.LOITER_SECONDS
            )
        )


        # =====================================================
        # BORDER HYSTERESIS
        # =====================================================

        # Prevents repeated SAFE/RESTRICTED flipping
        # when a person's box jitters around the border.
        self.BORDER_MARGIN = int(
            self.width * 0.025
        )

        self.safe_boundary = (
            self.restricted_x
            -
            self.BORDER_MARGIN
        )

        self.restricted_boundary = (
            self.restricted_x
            +
            self.BORDER_MARGIN
        )


        # Require the new side to remain stable
        # for several frames before a crossing counts.
        self.CROSSING_CONFIRM_FRAMES = max(
            4,
            int(
                self.fps * 0.18
            )
        )


        # =====================================================
        # RAW TRACK DATA
        # =====================================================

        self.track_hits = {}

        self.track_last_center = {}

        self.track_last_bbox = {}

        self.track_last_frame = {}

        # raw ByteTrack ID -> stable encounter ID
        self.track_to_encounter = {}


        # =====================================================
        # CONFIRMED ENCOUNTERS
        # =====================================================

        self.next_encounter_id = 1

        self.encounters = {}


        # =====================================================
        # EVENT QUEUES
        # =====================================================

        self.new_encounters = []

        self.new_intrusions = []

        self.new_loitering_alerts = []

        self.new_crossings = []


    # =========================================================
    # BOX AREA
    # =========================================================

    def box_area(
        self,
        bbox
    ):

        x1, y1, x2, y2 = bbox

        return max(
            0,
            x2 - x1
        ) * max(
            0,
            y2 - y1
        )


    # =========================================================
    # BOX CENTER
    # =========================================================

    def center(
        self,
        bbox
    ):

        x1, y1, x2, y2 = bbox

        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0
        )


    # =========================================================
    # DISTANCE
    # =========================================================

    def distance(
        self,
        p1,
        p2
    ):

        return math.hypot(
            p1[0] - p2[0],
            p1[1] - p2[1]
        )


    # =========================================================
    # IOU
    # =========================================================

    def iou(
        self,
        box1,
        box2
    ):

        x1 = max(
            box1[0],
            box2[0]
        )

        y1 = max(
            box1[1],
            box2[1]
        )

        x2 = min(
            box1[2],
            box2[2]
        )

        y2 = min(
            box1[3],
            box2[3]
        )


        intersection = max(
            0,
            x2 - x1
        ) * max(
            0,
            y2 - y1
        )


        if intersection <= 0:
            return 0.0


        area1 = self.box_area(
            box1
        )

        area2 = self.box_area(
            box2
        )


        union = (
            area1
            +
            area2
            -
            intersection
        )


        if union <= 0:
            return 0.0


        return (
            intersection /
            union
        )


    # =========================================================
    # SIZE SIMILARITY
    # =========================================================

    def size_similarity(
        self,
        box1,
        box2
    ):

        area1 = self.box_area(
            box1
        )

        area2 = self.box_area(
            box2
        )


        if (
            area1 <= 0 or
            area2 <= 0
        ):

            return 0.0


        smaller = min(
            area1,
            area2
        )

        larger = max(
            area1,
            area2
        )


        return (
            smaller /
            larger
        )


    # =========================================================
    # VELOCITY
    # =========================================================

    def calculate_velocity(
        self,
        encounter
    ):

        previous_center = (
            encounter.get(
                "previous_center"
            )
        )

        last_center = (
            encounter.get(
                "last_center"
            )
        )

        previous_frame = (
            encounter.get(
                "previous_frame"
            )
        )

        last_frame = (
            encounter.get(
                "last_frame"
            )
        )


        if (
            previous_center is None
            or
            last_center is None
            or
            previous_frame is None
            or
            last_frame is None
        ):

            return (
                0.0,
                0.0
            )


        frame_gap = (
            last_frame -
            previous_frame
        )


        if frame_gap <= 0:

            return (
                0.0,
                0.0
            )


        velocity_x = (
            last_center[0]
            -
            previous_center[0]
        ) / frame_gap


        velocity_y = (
            last_center[1]
            -
            previous_center[1]
        ) / frame_gap


        return (
            velocity_x,
            velocity_y
        )


    # =========================================================
    # PREDICT POSITION
    # =========================================================

    def predict_center(
        self,
        encounter,
        frame_number
    ):

        last_center = (
            encounter[
                "last_center"
            ]
        )


        frame_gap = (
            frame_number
            -
            encounter[
                "last_frame"
            ]
        )


        velocity_x, velocity_y = (
            self.calculate_velocity(
                encounter
            )
        )


        predicted_x = (
            last_center[0]
            +
            velocity_x *
            frame_gap
        )


        predicted_y = (
            last_center[1]
            +
            velocity_y *
            frame_gap
        )


        return (
            predicted_x,
            predicted_y
        )


    # =========================================================
    # INITIAL SIDE
    # =========================================================

    def get_initial_side(
        self,
        center_x
    ):

        if (
            center_x >=
            self.restricted_x
        ):

            return "RESTRICTED"

        return "SAFE"


    # =========================================================
    # SIDE WITH HYSTERESIS
    # =========================================================

    def get_side_with_hysteresis(
        self,
        center_x,
        previous_side
    ):

        if previous_side == "SAFE":

            if (
                center_x >=
                self.restricted_boundary
            ):

                return "RESTRICTED"

            return "SAFE"


        if previous_side == "RESTRICTED":

            if (
                center_x <=
                self.safe_boundary
            ):

                return "SAFE"

            return "RESTRICTED"


        return self.get_initial_side(
            center_x
        )


    # =========================================================
    # CREATE ENCOUNTER
    # =========================================================

    def create_encounter(
        self,
        raw_track_id,
        bbox,
        frame_number
    ):

        encounter_id = (
            self.next_encounter_id
        )

        self.next_encounter_id += 1


        now = datetime.now()

        center = self.center(
            bbox
        )


        side = self.get_initial_side(
            center[0]
        )


        self.encounters[
            encounter_id
        ] = {

            "encounter_id":
                encounter_id,

            "raw_track_ids":
                {raw_track_id},

            "first_seen":
                now,

            "last_seen":
                now,

            "first_frame":
                frame_number,

            "last_frame":
                frame_number,

            "previous_frame":
                None,

            "last_center":
                center,

            "previous_center":
                None,

            "last_bbox":
                bbox,

            "previous_bbox":
                None,

            "side":
                side,

            "candidate_side":
                side,

            "candidate_side_frames":
                0,

            "intrusion":
                False,

            "intrusion_frame":
                None,

            "restricted_start_frame":
                (
                    frame_number
                    if side ==
                    "RESTRICTED"
                    else None
                ),

            "loitering_alerted":
                False,

            "crossings":
                0,

            "status":
                (
                    "INTRUSION"
                    if side ==
                    "RESTRICTED"
                    else "NORMAL"
                )
        }


        self.track_to_encounter[
            raw_track_id
        ] = encounter_id


        self.new_encounters.append(
            encounter_id
        )


        # If first confirmed while already in restricted zone
        if side == "RESTRICTED":

            self.encounters[
                encounter_id
            ][
                "intrusion"
            ] = True


            self.encounters[
                encounter_id
            ][
                "intrusion_frame"
            ] = frame_number


            self.new_intrusions.append(
                encounter_id
            )


        return encounter_id


    # =========================================================
    # FIND RECENT ENCOUNTER
    # =========================================================

    def find_recent_encounter(
        self,
        bbox,
        frame_number
    ):

        new_center = self.center(
            bbox
        )


        best_encounter = None

        best_score = float(
            "inf"
        )


        for (
            encounter_id,
            encounter
        ) in self.encounters.items():

            frame_gap = (
                frame_number
                -
                encounter[
                    "last_frame"
                ]
            )


            # -------------------------------------------------
            # DO NOT MERGE WITH CURRENT ACTIVE PERSON
            # -------------------------------------------------

            if frame_gap <= 5:
                continue


            # -------------------------------------------------
            # TOO OLD
            # -------------------------------------------------

            if (
                frame_gap >
                self.RECONNECT_FRAMES
            ):

                continue


            # -------------------------------------------------
            # PREDICT POSITION
            # -------------------------------------------------

            predicted_center = (
                self.predict_center(
                    encounter,
                    frame_number
                )
            )


            position_distance = (
                self.distance(
                    new_center,
                    predicted_center
                )
            )


            # -------------------------------------------------
            # ALLOWED RECONNECT DISTANCE
            # -------------------------------------------------

            allowed_distance = (
                self.BASE_RECONNECT_DISTANCE
                +
                frame_gap * 2.0
            )


            allowed_distance = min(
                allowed_distance,
                self.MAX_RECONNECT_DISTANCE
            )


            if (
                position_distance >
                allowed_distance
            ):

                continue


            # -------------------------------------------------
            # BOX SIZE SIMILARITY
            # -------------------------------------------------

            size_score = (
                self.size_similarity(
                    bbox,
                    encounter[
                        "last_bbox"
                    ]
                )
            )


            if (
                size_score <
                self.MIN_SIZE_SIMILARITY
            ):

                continue


            # -------------------------------------------------
            # IOU
            # -------------------------------------------------

            overlap = self.iou(
                bbox,
                encounter[
                    "last_bbox"
                ]
            )


            # -------------------------------------------------
            # MATCH SCORE
            # -------------------------------------------------

            normalized_distance = (
                position_distance
                /
                max(
                    allowed_distance,
                    1
                )
            )


            size_penalty = (
                1.0 -
                size_score
            )


            score = (
                normalized_distance
                +
                size_penalty * 0.55
                -
                overlap * 0.50
            )


            if (
                score <
                best_score
            ):

                best_score = score

                best_encounter = (
                    encounter_id
                )


        if (
            best_encounter is None
            or
            best_score >
            self.MAX_MATCH_SCORE
        ):

            return None


        return best_encounter


    # =========================================================
    # RECONNECT RAW TRACK
    # =========================================================

    def reconnect_track(
        self,
        raw_track_id,
        encounter_id
    ):

        self.track_to_encounter[
            raw_track_id
        ] = encounter_id


        self.encounters[
            encounter_id
        ][
            "raw_track_ids"
        ].add(
            raw_track_id
        )


    # =========================================================
    # UPDATE SIDE
    # =========================================================

    def update_side(
        self,
        encounter,
        center_x,
        frame_number,
        now
    ):

        previous_side = (
            encounter[
                "side"
            ]
        )


        proposed_side = (
            self.get_side_with_hysteresis(
                center_x,
                previous_side
            )
        )


        # No side change
        if (
            proposed_side ==
            previous_side
        ):

            encounter[
                "candidate_side"
            ] = previous_side

            encounter[
                "candidate_side_frames"
            ] = 0

            return previous_side


        # Candidate changed
        if (
            encounter[
                "candidate_side"
            ]
            !=
            proposed_side
        ):

            encounter[
                "candidate_side"
            ] = proposed_side

            encounter[
                "candidate_side_frames"
            ] = 1

        else:

            encounter[
                "candidate_side_frames"
            ] += 1


        # Wait for stable confirmation
        if (
            encounter[
                "candidate_side_frames"
            ]
            <
            self.CROSSING_CONFIRM_FRAMES
        ):

            return previous_side


        current_side = (
            proposed_side
        )


        encounter[
            "crossings"
        ] += 1


        if (
            previous_side ==
            "SAFE"
            and
            current_side ==
            "RESTRICTED"
        ):

            direction = (
                "SAFE -> RESTRICTED"
            )

        else:

            direction = (
                "RESTRICTED -> SAFE"
            )


        self.new_crossings.append({

            "encounter_id":
                encounter[
                    "encounter_id"
                ],

            "direction":
                direction,

            "frame":
                frame_number,

            "time":
                now
        })


        encounter[
            "side"
        ] = current_side


        encounter[
            "candidate_side"
        ] = current_side


        encounter[
            "candidate_side_frames"
        ] = 0


        return current_side


    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        raw_track_id,
        bbox,
        confidence,
        frame_number
    ):

        # -----------------------------------------------------
        # FILTER SMALL BOXES
        # -----------------------------------------------------

        if (
            self.box_area(
                bbox
            )
            <
            self.MIN_BOX_AREA
        ):

            return None


        center = self.center(
            bbox
        )


        # -----------------------------------------------------
        # RAW TRACK HIT COUNT
        # -----------------------------------------------------

        self.track_hits[
            raw_track_id
        ] = (
            self.track_hits.get(
                raw_track_id,
                0
            )
            +
            1
        )


        self.track_last_center[
            raw_track_id
        ] = center


        self.track_last_bbox[
            raw_track_id
        ] = bbox


        self.track_last_frame[
            raw_track_id
        ] = frame_number


        # -----------------------------------------------------
        # EXISTING TRACK
        # -----------------------------------------------------

        if (
            raw_track_id
            in
            self.track_to_encounter
        ):

            encounter_id = (
                self.track_to_encounter[
                    raw_track_id
                ]
            )


        # -----------------------------------------------------
        # NEW RAW TRACK
        # -----------------------------------------------------

        else:

            # Must survive enough frames
            if (
                self.track_hits[
                    raw_track_id
                ]
                <
                self.MIN_CONFIRM_FRAMES
            ):

                return None


            # Try reconnecting to a recently lost encounter
            encounter_id = (
                self.find_recent_encounter(
                    bbox,
                    frame_number
                )
            )


            if (
                encounter_id
                is not None
            ):

                self.reconnect_track(
                    raw_track_id,
                    encounter_id
                )


                print(
                    f"Reconnected raw track "
                    f"{raw_track_id} -> "
                    f"PERSON-{encounter_id:04d}"
                )


            else:

                encounter_id = (
                    self.create_encounter(
                        raw_track_id,
                        bbox,
                        frame_number
                    )
                )


        encounter = (
            self.encounters[
                encounter_id
            ]
        )


        now = datetime.now()


        # -----------------------------------------------------
        # PREVIOUS MOTION STATE
        # -----------------------------------------------------

        encounter[
            "previous_center"
        ] = encounter.get(
            "last_center"
        )


        encounter[
            "previous_bbox"
        ] = encounter.get(
            "last_bbox"
        )


        encounter[
            "previous_frame"
        ] = encounter.get(
            "last_frame"
        )


        # -----------------------------------------------------
        # CURRENT STATE
        # -----------------------------------------------------

        encounter[
            "last_center"
        ] = center


        encounter[
            "last_bbox"
        ] = bbox


        encounter[
            "last_frame"
        ] = frame_number


        encounter[
            "last_seen"
        ] = now


        # -----------------------------------------------------
        # BORDER SIDE
        # -----------------------------------------------------

        current_side = self.update_side(

            encounter,

            center[0],

            frame_number,

            now
        )


        # -----------------------------------------------------
        # RESTRICTED ZONE
        # -----------------------------------------------------

        if (
            current_side ==
            "RESTRICTED"
        ):

            if (
                encounter[
                    "restricted_start_frame"
                ]
                is None
            ):

                encounter[
                    "restricted_start_frame"
                ] = frame_number


            if not encounter[
                "intrusion"
            ]:

                encounter[
                    "intrusion"
                ] = True


                encounter[
                    "intrusion_frame"
                ] = frame_number


                encounter[
                    "status"
                ] = "INTRUSION"


                self.new_intrusions.append(
                    encounter_id
                )


            # -------------------------------------------------
            # LOITERING
            # -------------------------------------------------

            restricted_frames = (
                frame_number
                -
                encounter[
                    "restricted_start_frame"
                ]
            )


            if (
                restricted_frames
                >=
                self.LOITER_FRAMES
                and
                not encounter[
                    "loitering_alerted"
                ]
            ):

                encounter[
                    "loitering_alerted"
                ] = True


                encounter[
                    "status"
                ] = "LOITERING"


                self.new_loitering_alerts.append(
                    encounter_id
                )


        # -----------------------------------------------------
        # SAFE SIDE
        # -----------------------------------------------------

        else:

            encounter[
                "restricted_start_frame"
            ] = None


            if (
                not encounter[
                    "intrusion"
                ]
                and
                not encounter[
                    "loitering_alerted"
                ]
            ):

                encounter[
                    "status"
                ] = "NORMAL"


        # =====================================================
        # RETURN DATA TO VIDEO_SYSTEM.PY
        # =====================================================

        return {

            "encounter_id":
                encounter_id,

            "status":
                encounter[
                    "status"
                ],

            "side":
                current_side,

            "center": (
                int(
                    center[0]
                ),
                int(
                    center[1]
                )
            ),

            "crossings":
                encounter[
                    "crossings"
                ],

            "loitering":
                encounter[
                    "loitering_alerted"
                ],

            "intrusion":
                encounter[
                    "intrusion"
                ],

            "confidence":
                confidence,

            "raw_track_id":
                raw_track_id,

            "first_seen":
                encounter[
                    "first_seen"
                ],

            "last_seen":
                encounter[
                    "last_seen"
                ]
        }


    # =========================================================
    # TOTAL CONFIRMED PEOPLE
    # =========================================================

    def total_people(
        self
    ):

        return len(
            self.encounters
        )


    # =========================================================
    # GET ENCOUNTER
    # =========================================================

    def get_encounter(
        self,
        encounter_id
    ):

        return self.encounters.get(
            encounter_id
        )


    # =========================================================
    # GET ALL ENCOUNTERS
    # =========================================================

    def get_all_encounters(
        self
    ):

        return self.encounters