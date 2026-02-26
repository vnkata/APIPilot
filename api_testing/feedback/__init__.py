from api_testing.utils.http import isSuccessful

class FeedbackAnalyzer:
	def __init__(self,model=None):
		self.model = model
	def evaluate(self, responses):
		
		invalids = [ entry for entry in responses if not entry.get("is_expected_status",True) ] # lấy những response không thỏa mong đợi
		
		print(invalids)
        