class Place {
  const Place({
    required this.id,
    required this.sentence,
    required this.created,
    this.parked = false,
    this.finished = false,
    this.delivery = 'local',
    this.mailId,
    this.headStart,
  });
  final String id, sentence, delivery;
  final String? mailId, headStart;
  final DateTime created;
  final bool parked, finished;
  Place copyWith({
    bool? parked,
    bool? finished,
    String? delivery,
    String? mailId,
    String? headStart,
  }) => Place(
    id: id,
    sentence: sentence,
    created: created,
    parked: parked ?? this.parked,
    finished: finished ?? this.finished,
    delivery: delivery ?? this.delivery,
    mailId: mailId ?? this.mailId,
    headStart: headStart ?? this.headStart,
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'sentence': sentence,
    'created': created.toIso8601String(),
    'parked': parked,
    'finished': finished,
    'delivery': delivery,
    'mail_id': mailId,
    'head_start': headStart,
  };
  factory Place.fromJson(Map<String, dynamic> value) => Place(
    id: value['id'] as String,
    sentence: value['sentence'] as String,
    created: DateTime.parse(value['created'] as String),
    parked: value['parked'] == true,
    finished: value['finished'] == true,
    delivery: value['delivery'] as String? ?? 'local',
    mailId: value['mail_id'] as String?,
    headStart: value['head_start'] as String?,
  );
}
