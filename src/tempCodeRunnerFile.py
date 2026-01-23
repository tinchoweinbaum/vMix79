    def adelantaVideo(self, inputNum, segundos):
            ms = segundos * 1000
            # El formato debe ser "+5000" para adelantar 5 seg.
            # Sin el "=", solo el signo "+"
            self.__makeRequest("SetPosition", extraParams={
                "Value": f"+{ms}", 
                "Input": inputNum
            })