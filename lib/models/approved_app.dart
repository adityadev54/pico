class ApprovedApp {
  const ApprovedApp({required this.id, required this.name});
  final String id, name;
  factory ApprovedApp.fromJson(Map<String, dynamic> json) =>
      ApprovedApp(id: json['id'] as String, name: json['name'] as String);
}
