class ActivityEntry {
  const ActivityEntry({
    required this.id,
    required this.title,
    required this.detail,
    required this.created,
    required this.target,
  });
  final String id, title, detail, target;
  final DateTime created;
  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'detail': detail,
    'created': created.toIso8601String(),
    'target': target,
  };
  factory ActivityEntry.fromJson(Map<String, dynamic> value) => ActivityEntry(
    id: value['id'],
    title: value['title'],
    detail: value['detail'],
    created: DateTime.parse(value['created']),
    target: value['target'],
  );
}
