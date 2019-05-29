SELECT @BOARD_UUID := '220e9130-2d89-435e-96c1-49f9c88f9a18';


select @BOARD_ID := `id`  from boards where uuid= @BOARD_UUID;
delete from locations where board_id=@BOARD_ID;
delete from sessions where board_id=@BOARD_ID;
delete from enabled_webservices where board_uuid=@BOARD_UUID;
delete from exposed_services where board_uuid=@BOARD_UUID;
delete from webservices where board_uuid=@BOARD_UUID;
delete from injection_plugins where board_uuid=@BOARD_UUID;
delete from boards where uuid=@BOARD_UUID;