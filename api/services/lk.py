"""LiveKit service for managing rooms, tokens, and egress."""

import secrets
from livekit import api
from config import settings


class LiveKitService:
    """Service for interacting with LiveKit server."""

    def __init__(self) -> None:
        """Initialize the LiveKit service."""
        self.api_key = settings.livekit_api_key
        self.api_secret = settings.livekit_api_secret
        self.url = settings.livekit_url

    def generate_room_name(self) -> str:
        """Generate a unique room name for a streaming session.

        Returns:
            A unique room name string
        """
        return f"blindsighted-{secrets.token_urlsafe(16)}"

    async def create_room(self, room_name: str) -> api.Room:
        """Create a new LiveKit room.

        Args:
            room_name: Name of the room to create

        Returns:
            The created Room object
        """
        lkapi = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        room_service = lkapi.room()

        room = await room_service.create_room(
            api.CreateRoomRequest(name=room_name)
        )
        await lkapi.aclose()
        return room

    def create_access_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str | None = None,
    ) -> str:
        """Create an access token for a participant to join a room.

        Args:
            room_name: Name of the room
            participant_identity: Unique identity for the participant
            participant_name: Display name for the participant

        Returns:
            Access token string
        """
        token = api.AccessToken(self.api_key, self.api_secret)
        token.with_identity(participant_identity)
        token.with_name(participant_name or participant_identity)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        return token.to_jwt()

    async def start_room_composite_egress(
        self,
        room_name: str,
        r2_key: str,
    ) -> api.EgressInfo:
        """Start room composite egress to record the entire room.

        Args:
            room_name: Name of the room to record
            r2_key: S3/R2 key path for the recording

        Returns:
            EgressInfo object with egress details
        """
        lkapi = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        egress_service = lkapi.egress()

        # Configure S3 (R2-compatible) upload
        s3_upload = api.S3Upload(
            access_key=settings.r2_access_key_id,
            secret=settings.r2_secret_access_key,
            region="auto",
            endpoint=f"https://{settings.cloudflare_account_id}.r2.cloudflarestorage.com",
            bucket=settings.r2_bucket_name,
        )

        # Start room composite egress
        egress_info = await egress_service.start_room_composite_egress(
            api.RoomCompositeEgressRequest(
                room_name=room_name,
                file_outputs=[
                    api.EncodedFileOutput(
                        file_type=api.EncodedFileType.MP4,
                        filepath=r2_key,
                        s3=s3_upload,
                    )
                ],
            )
        )

        await lkapi.aclose()
        return egress_info

    async def stop_egress(self, egress_id: str) -> api.EgressInfo:
        """Stop an active egress.

        Args:
            egress_id: ID of the egress to stop

        Returns:
            Updated EgressInfo object
        """
        lkapi = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        egress_service = lkapi.egress()

        egress_info = await egress_service.stop_egress(
            api.StopEgressRequest(egress_id=egress_id)
        )

        await lkapi.aclose()
        return egress_info

    async def delete_room(self, room_name: str) -> None:
        """Delete a LiveKit room.

        Args:
            room_name: Name of the room to delete
        """
        lkapi = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        room_service = lkapi.room()

        await room_service.delete_room(
            api.DeleteRoomRequest(room=room_name)
        )
        await lkapi.aclose()
