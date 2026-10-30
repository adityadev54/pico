class Place {
  const Place({
    required this.id,
    required this.sentence,
    required this.created,
    this.parked = false,
    this.finished = false,
    this.delivery = 'local',
    this.role = 'user',
    this.mailId,
    this.headStart,
    this.chatId,
    this.deliveryDeviceId,
  });
  final String id, sentence, delivery, role;
  final String? mailId, headStart, chatId, deliveryDeviceId;
  final DateTime created;
  final bool parked, finished;
  Place copyWith({
    bool? parked,
    bool? finished,
    String? delivery,
    String? mailId,
    String? headStart,
    String? chatId,
    String? deliveryDeviceId,
  }) => Place(
    id: id,
    role: role,
    sentence: sentence,
    created: created,
    parked: parked ?? this.parked,
    finished: finished ?? this.finished,
    delivery: delivery ?? this.delivery,
    mailId: mailId ?? this.mailId,
    headStart: headStart ?? this.headStart,
    chatId: chatId ?? this.chatId,
    deliveryDeviceId: deliveryDeviceId ?? this.deliveryDeviceId,
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'sentence': sentence,
    'role': role,
    'created': created.toIso8601String(),
    'parked': parked,
    'finished': finished,
    'delivery': delivery,
    'mail_id': mailId,
    'head_start': headStart,
    'chat_id': chatId,
    'delivery_device_id': deliveryDeviceId,
  };
  factory Place.fromJson(Map<String, dynamic> value) => Place(
    id: value['id'] as String,
    sentence: value['sentence'] as String,
    role: value['role'] == 'assistant' ? 'assistant' : 'user',
    created: DateTime.parse(value['created'] as String),
    parked: value['parked'] == true,
    finished: value['finished'] == true,
    delivery: value['delivery'] as String? ?? 'local',
    mailId: value['mail_id'] as String?,
    headStart: value['head_start'] as String?,
    chatId: value['chat_id'] as String?,
    deliveryDeviceId: value['delivery_device_id'] as String?,
  );
}
